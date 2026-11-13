"""Parcours de contrôle dans un vrai navigateur : chaque page s'affiche et s'hydrate sans erreur
(exception, hydratation, politique de sécurité du contenu), et les gestes essentiels marchent
(choisir une taille, ajouter au panier, filtrer par couleur). Les services, la boutique et un
compte de l'équipe doivent tourner (voir .github/workflows/ci.yml).

    python essais/balayage.py            # BIBOU_ADRESSE=http://localhost:3000 par défaut
"""

import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

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
    "/gestion/avis", "/gestion/tenues", "/gestion/codes-promo", "/atelier", "/mon-compte", "/mes-commandes", "/composer",
]
# Bruit sans conséquence : session absente (401), préchargements servis par le service worker.
IGNORES = ("401", "cross-world service worker")


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

        for chemin in PUBLIQUES:
            courante["chemin"] = chemin
            page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
            if page.evaluate("document.documentElement.scrollWidth") > 391:
                erreurs.append(f"{chemin} : la page déborde de l'écran du téléphone")

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
        navigateur.close()

    print(f"{len(PUBLIQUES) + len(EQUIPE)} pages parcourues.")
    for erreur in erreurs:
        print("ERREUR", erreur)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
