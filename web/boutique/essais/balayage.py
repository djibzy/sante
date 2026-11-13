"""Parcours de contrôle dans un vrai navigateur : chaque page s'affiche et s'hydrate sans erreur
(exception, hydratation, politique de sécurité du contenu), passe les règles d'accessibilité
WCAG 2.1 A et AA vérifiées par axe-core (défauts graves et critiques), et les gestes essentiels
marchent (choisir une taille, ajouter au panier, commander, filtrer par couleur, corriger les
articles d'une commande, faire payer un proche, encaisser, annuler, rembourser, commander à
nouveau). Les services, la boutique et un
compte de l'équipe doivent tourner (voir .github/workflows/ci.yml).

    python essais/balayage.py            # BIBOU_ADRESSE=http://localhost:3000 par défaut
"""

import os
import re
import sys
from contextlib import suppress
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, Page, Response, expect, sync_playwright

ADRESSE = os.environ.get("BIBOU_ADRESSE", "http://localhost:3000")
TELEPHONE = os.environ.get("BIBOU_EQUIPE_TELEPHONE", "70 00 00 01")
MOT_DE_PASSE = os.environ.get("BIBOU_EQUIPE_MOT_DE_PASSE", "bibou-equipe-2026")
PUBLIQUES = [
    "/", "/tenues-medicales", "/rayons/blouses-medicales", "/rayons/chaussures", "/metiers/infirmier",
    "/produits/kit-hygiene", "/produits/blouse-medicale-brodee", "/produits/tunique-col-v?couleur=Bordeaux",
    "/produits/baskets-soignant", "/produits/gants-steriles", "/panier", "/commande", "/devis",
    "/recherche?q=blouse", "/favoris", "/guide-des-tailles", "/broderie", "/services", "/hors-ligne",
    "/conditions", "/confidentialite", "/mentions-legales", "/connexion", "/inscription",
    "/mot-de-passe-oublie", "/nouveautes", "/promotions", "/explorer", "/explorer?famille=bleu",
    "/explorer?proche=1f4fa8", "/composer", "/composer?vide=1", "/commande-equipe",
    "/commande-equipe?produit=blouse-medicale-brodee", "/collection/Wax", "/univers/equipement",
]
EQUIPE = [
    "/gestion/tableau-de-bord", "/gestion", "/gestion/livraisons", "/gestion/stock", "/gestion/catalogue",
    "/gestion/avis", "/gestion/tenues", "/gestion/codes-promo", "/gestion?onglet=a-rembourser", "/atelier",
    "/mon-compte", "/mes-commandes", "/composer",
]
# Bruit sans conséquence : session absente (401), préchargements servis par le service worker.
# 401 : pages de l'équipe avant connexion. NUXT_E5002 : le manifeste de l'application, demandé
# en arrière-plan, interrompu quand le test passe aussitôt à la page suivante (sans effet).
IGNORES = ("401", "cross-world service worker", "NUXT_E5002")
AXE = (Path(__file__).resolve().parents[1] / "node_modules" / "axe-core" / "axe.min.js").read_text()
REGLES = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]


def accessibilite(page: Page) -> list[str]:
    """Défauts graves ou critiques relevés par axe-core sur la page affichée."""
    page.evaluate(AXE)
    defauts = page.evaluate(
        """async (regles) => (await axe.run(document, { runOnly: { type: 'tag', values: regles } }))
          .violations.filter(v => ['serious', 'critical'].includes(v.impact))
          .map(v => `${v.id} (${v.nodes.length}) : ${v.nodes[0].target.join(' ')}`)""",
        REGLES,
    )
    return list(defauts)


# Premier chargement (cache vide) des pages d'entrée, en octets non compressés : sur un forfait
# mobile, chaque centaine de kilo-octets compte. Aujourd'hui entre 330 et 490 Ko.
BUDGET_OCTETS = 600_000
PAGES_D_ENTREE = ("/", "/produits/blouse-medicale-brodee", "/explorer", "/panier")


def poids(navigateur: Browser, chemin: str) -> int:
    contexte = navigateur.new_context(viewport={"width": 390, "height": 844})
    page = contexte.new_page()
    total = 0

    def compter(reponse: Response) -> None:
        nonlocal total
        with suppress(Exception):  # redirection, réponse sans corps
            total += len(reponse.body())

    page.on("response", compter)
    page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
    contexte.close()
    return total


def main() -> int:
    erreurs: list[str] = []
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        page = navigateur.new_context(viewport={"width": 390, "height": 844}).new_page()
        courante = {"chemin": ""}

        def noter(texte: str) -> None:
            if not any(i in texte for i in IGNORES):
                erreurs.append(f"{courante['chemin']} : {texte}")

        page.on("pageerror", lambda e: noter(f"exception : {e}"))
        page.on("console", lambda m: noter(m.text) if m.type in ("error", "warning") else None)

        for chemin in PAGES_D_ENTREE:
            octets = poids(navigateur, chemin)
            if octets > BUDGET_OCTETS:
                erreurs.append(f"{chemin} : {octets // 1000} Ko au premier chargement (budget 600)")

        for chemin in PUBLIQUES:
            courante["chemin"] = chemin
            page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
            if page.evaluate("document.documentElement.scrollWidth") > 391:
                erreurs.append(f"{chemin} : la page déborde de l'écran du téléphone")
            erreurs.extend(f"{chemin} : accessibilité, {d}" for d in accessibilite(page))

        # Gestes essentiels : taille conseillée, ajout au panier, filtre par couleur.
        courante["chemin"] = "parcours d'achat"
        page.goto(f"{ADRESSE}/produits/tunique-col-v", wait_until="networkidle")
        page.get_by_text("Quelle taille choisir ?").click()
        page.get_by_label("Tour de poitrine (cm)").fill("93")
        page.get_by_role("button", name="Choisir M").click()
        page.get_by_role("button", name="Ajouter au panier").click()
        page.goto(f"{ADRESSE}/panier", wait_until="networkidle")
        expect(page.locator(".ligne")).to_have_count(1)
        expect(page.locator(".ligne")).to_contain_text("M")
        page.goto(f"{ADRESSE}/commande", wait_until="networkidle")
        page.get_by_label("Prénom et nom").fill("Awa Sidibé")
        page.get_by_label("Téléphone").fill(os.environ.get("BIBOU_CLIENT_TELEPHONE", "76 45 12 50"))
        if page.get_by_label("J'ai compris").count():  # article fait à la demande : acompte
            page.get_by_label("J'ai compris").check()
        page.get_by_role("button", name="Confirmer la commande").click()
        page.wait_for_url(re.compile(r"/suivi/"))
        reference = page.url.split("/suivi/")[1].split("?")[0]
        suivi = page.url
        page.goto(f"{ADRESSE}/explorer", wait_until="networkidle")
        page.get_by_role("button", name=re.compile("Bleus")).click()
        page.wait_for_url(re.compile(r"famille=bleu"))
        expect(page.locator(".compte")).to_contain_text("bleus")

        courante["chemin"] = "/connexion (équipe)"
        page.goto(f"{ADRESSE}/connexion?retour=/gestion", wait_until="networkidle")
        page.get_by_label("Numéro de téléphone").fill(TELEPHONE)
        page.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
        page.get_by_role("button", name="Se connecter").click()
        page.wait_for_url(f"{ADRESSE}/gestion")
        for chemin in EQUIPE:
            courante["chemin"] = chemin
            page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
            erreurs.extend(f"{chemin} : accessibilité, {d}" for d in accessibilite(page))

        # La commande passée plus haut, ouverte par l'équipe, articles en cours de correction.
        chemin = f"/gestion/commandes/{reference}"
        courante["chemin"] = chemin
        page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
        page.get_by_role("button", name="Corriger les articles").click()
        expect(page.locator(".ligne-article")).to_have_count(1)
        if page.evaluate("document.documentElement.scrollWidth") > 391:
            erreurs.append(f"{chemin} : la correction des articles déborde de l'écran du téléphone")
        erreurs.extend(f"{chemin} : accessibilité, {d}" for d in accessibilite(page))

        # Confirmée : le client envoie un lien de paiement à un proche, qui ouvre sa page.
        page.get_by_role("button", name="Abandonner").click()
        page.get_by_role("button", name="Confirmer la commande").click()
        expect(page.get_by_role("button", name="Confirmer la commande")).to_have_count(0)
        proche = navigateur.new_context(viewport={"width": 390, "height": 844}).new_page()
        proche.on("pageerror", lambda e: noter(f"exception : {e}"))
        proche.goto(suivi, wait_until="networkidle")
        proche.get_by_role("button", name="Faire payer par un proche").click()
        envoi = proche.locator(".paiement").get_by_role("link", name="Envoyer sur WhatsApp")
        expect(envoi).to_be_visible()
        texte = envoi.get_attribute("href")
        lien = parse_qs(urlsplit(texte or "").query)["text"][0].split("Lien sécurisé : ")[1]
        courante["chemin"] = f"/payer/{reference}"
        proche.goto(lien, wait_until="networkidle")
        expect(proche.locator(".reste")).to_be_visible()
        if proche.evaluate("document.documentElement.scrollWidth") > 391:
            erreurs.append(f"/payer/{reference} : la page déborde de l'écran du téléphone")
        erreurs.extend(f"/payer/{reference} : accessibilité, {d}" for d in accessibilite(proche))
        proche.context.close()
        courante["chemin"] = chemin

        # Encaissée puis annulée par la boutique : tout est à rendre, le formulaire apparaît.
        page.get_by_role("button", name="Enregistrer l'encaissement").click()
        expect(page.locator(".paiements li")).to_have_count(1)
        if page.get_by_label("Par la boutique", exact=False).count():  # acompte payé
            page.get_by_label("Par la boutique", exact=False).check()
        page.get_by_role("button", name="Annuler", exact=True).click()
        expect(page.locator(".remboursement")).to_be_visible()
        if page.evaluate("document.documentElement.scrollWidth") > 391:
            erreurs.append(f"{chemin} : le remboursement déborde de l'écran du téléphone")
        erreurs.extend(f"{chemin} (remboursement) : accessibilité, {d}" for d in accessibilite(page))
        page.get_by_role("button", name="Enregistrer le remboursement").click()
        expect(page.locator(".remboursement")).to_have_count(0)
        expect(page.locator(".rendus li")).to_have_count(1)

        # Annulée : le client remet les mêmes articles dans son panier.
        cliente = navigateur.new_context(viewport={"width": 390, "height": 844}).new_page()
        cliente.on("pageerror", lambda e: noter(f"exception : {e}"))
        cliente.goto(suivi, wait_until="networkidle")
        cliente.get_by_role("button", name="Commander à nouveau").click()
        cliente.wait_for_url(f"{ADRESSE}/panier")
        expect(cliente.locator(".reprise")).to_contain_text(reference)
        expect(cliente.locator(".ligne")).to_have_count(1)
        courante["chemin"] = "/panier (commander à nouveau)"
        erreurs.extend(f"/panier (reprise) : accessibilité, {d}" for d in accessibilite(cliente))
        navigateur.close()

    print(f"{len(PUBLIQUES) + len(EQUIPE) + 2} pages parcourues.")
    for erreur in erreurs:
        print("ERREUR", erreur)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
