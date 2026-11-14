"""Parcours de contrôle de l'entretien du linge, dans un vrai navigateur : chaque page s'affiche
et s'hydrate sans erreur, passe les règles WCAG 2.1 A et AA vérifiées par axe-core (défauts
graves et critiques), ne déborde pas d'un écran de téléphone, et le service marche de bout en
bout : une structure demande une visite, la gestion signe le contrat, l'agent enlève le linge en
le comptant, le dépose chez le partenaire, le rend avec une pièce manquante, le relevé du mois
tombe juste ; l'agent de terrain n'a pas accès à la gestion.

Les services, l'interface, les données de démonstration (prestations.donnees_demo) et deux
comptes de l'équipe doivent exister (voir .github/workflows/ci.yml).

    python essais/parcours.py        # PRESTATIONS_ADRESSE=http://localhost:3001 par défaut
"""

import os
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright

ADRESSE = os.environ.get("PRESTATIONS_ADRESSE", "http://localhost:3001")
GESTION = os.environ.get("PRESTATIONS_GESTION_TELEPHONE", "70 00 00 03")
TERRAIN = os.environ.get("PRESTATIONS_TERRAIN_TELEPHONE", "70 00 00 04")
MOT_DE_PASSE = os.environ.get("PRESTATIONS_MOT_DE_PASSE", "prestations-equipe-2026")
AXE = (Path(__file__).resolve().parents[1] / "node_modules" / "axe-core" / "axe.min.js").read_text()
REGLES = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
# 401 : pages de l'équipe avant connexion. NUXT_E5002 : manifeste interrompu par la navigation.
IGNORES = ("401", "NUXT_E5002")
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def retour_promis(depart: datetime, jours: int) -> str:
    jour = depart.date()
    while jours:
        jour += timedelta(days=1)
        if jour.isoweekday() != 7:
            jours -= 1
    return jour.isoformat()


class Controle:
    def __init__(self, navigateur: Browser) -> None:
        self.navigateur = navigateur
        self.erreurs: list[str] = []
        self.etape = ""

    def contexte(self, largeur: int = 390) -> BrowserContext:
        contexte = self.navigateur.new_context(viewport={"width": largeur, "height": 844})
        contexte.on("console", lambda m: self.noter(m.text) if m.type == "error" else None)
        contexte.on("page", lambda page: page.on("pageerror", lambda e: self.noter(f"exception : {e}")))
        return contexte

    def noter(self, texte: str) -> None:
        if not any(i in texte for i in IGNORES):
            self.erreurs.append(f"{self.etape} : {texte}")

    def verifier(self, page: Page, etape: str) -> None:
        """Accessibilité et largeur, sur la page telle qu'elle est affichée."""
        self.etape = etape
        page.evaluate(AXE)
        defauts = page.evaluate(
            """async (regles) => (await axe.run(document, { runOnly: { type: 'tag', values: regles } }))
              .violations.filter(v => ['serious', 'critical'].includes(v.impact))
              .map(v => `${v.id} (${v.nodes.length}) : ${v.nodes[0].target.join(' ')}`)""",
            REGLES,
        )
        self.erreurs.extend(f"{etape} : accessibilité, {d}" for d in defauts)
        largeur = page.viewport_size["width"] if page.viewport_size else 390
        if page.evaluate("document.documentElement.scrollWidth") > largeur + 1:
            self.erreurs.append(f"{etape} : la page déborde de l'écran")


def connecter(controle: Controle, telephone: str, largeur: int = 390) -> Page:
    page = controle.contexte(largeur).new_page()
    page.goto(f"{ADRESSE}/connexion", wait_until="networkidle")
    page.get_by_label("Numéro de téléphone").fill(telephone)
    page.get_by_label("Mot de passe").fill(MOT_DE_PASSE)
    page.get_by_role("button", name="Se connecter").click()
    page.wait_for_url(f"{ADRESSE}/equipe")
    page.wait_for_load_state("networkidle")
    return page


def main() -> int:
    maintenant = datetime.now(UTC)
    jour_du_contrat = JOURS[maintenant.isoweekday() - 1]
    structure = f"Clinique Parcours {random.randint(1000, 9999)}"
    telephone = f"7{random.randint(1, 9)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
    with sync_playwright() as p:
        controle = Controle(p.chromium.launch())

        # La structure découvre l'offre et demande une visite.
        page = controle.contexte().new_page()
        for chemin in ("/", "/entretien-du-linge", "/connexion"):
            page.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
            controle.verifier(page, chemin)
        page.goto(f"{ADRESSE}/entretien-du-linge", wait_until="networkidle")
        page.get_by_label("Nombre de lits").fill("20")
        page.get_by_label("Soignants en tenue").fill("10")
        expect(page.get_by_text("Environ 210 pièces par semaine")).to_be_visible()
        page.get_by_role("button", name="Reporter dans ma demande").click()
        page.get_by_label("Nom de la structure").fill(structure)
        page.get_by_label("Type de structure").select_option("clinique")
        page.get_by_label("Votre nom et votre fonction").fill("Awa Traoré, surveillante générale")
        page.get_by_label("Téléphone").fill(telephone)
        page.get_by_label("Quartier et ville").fill("Badalabougou, Bamako")
        page.get_by_role("button", name="Envoyer la demande").click()
        expect(page.get_by_role("heading", name="Demande envoyée")).to_be_visible()
        controle.verifier(page, "demande envoyée")

        # La gestion rappelle, puis signe le contrat (collecte le jour même, à la pièce).
        gestion = connecter(controle, GESTION, 1280)
        for chemin in ("/equipe", "/equipe/demandes", "/equipe/contrats", "/equipe/partenaires", "/equipe/releves"):
            gestion.goto(f"{ADRESSE}{chemin}", wait_until="networkidle")
            controle.verifier(gestion, chemin)
        gestion.goto(f"{ADRESSE}/equipe/demandes", wait_until="networkidle")
        carte = gestion.locator(".demande", has_text=structure)
        expect(carte).to_contain_text("210 pièces par semaine")
        carte.get_by_role("link", name="Signer le contrat").click()
        gestion.wait_for_url("**/equipe/contrats/nouveau?demande=*")
        expect(gestion.get_by_label("Nom", exact=True)).to_have_value(structure)
        gestion.get_by_label(jour_du_contrat, exact=True).check()
        gestion.get_by_label("Retour promis (jours, dimanche exclu)").fill("2")
        gestion.get_by_label("Partenaire par défaut").select_option(label="Pressing de démonstration")
        for article, prix in (("blouse", "500"), ("drap", "700"), ("taie", "250")):
            gestion.locator(f"#tarif-{article}").fill(prix)
        # Estimation du mois avec les volumes de la demande : 520 draps, 260 taies, 130 blouses.
        estimation = gestion.locator(".estimation")
        expect(estimation).to_contain_text("494 000 FCFA")
        expect(estimation).to_contain_text("208 000 FCFA (42 %)")
        controle.verifier(gestion, "nouveau contrat")
        gestion.get_by_role("button", name="Signer le contrat").click()
        gestion.wait_for_url("**/equipe/contrats/CT-*")
        contrat = gestion.url.rsplit("/", 1)[-1]

        # L'agent compte le linge à l'enlèvement, le dépose, puis le rend au jour promis.
        controle.etape = "tournée"
        agent = connecter(controle, TERRAIN)
        expect(agent.get_by_role("link", name="Demandes")).to_have_count(0)
        agent.goto(f"{ADRESSE}/equipe/tournee", wait_until="networkidle")
        passage = agent.locator(".passage", has_text=structure)
        passage.get_by_role("button", name="Enlever le linge").click()
        agent.locator(f"#enlevement-{contrat}-drap").fill("12")
        agent.locator(f"#enlevement-{contrat}-blouse").fill("5")
        plus = passage.get_by_role("button", name="Taie d'oreiller : une pièce de plus")
        plus.click()
        plus.click()
        passage.get_by_label("Remis par (nom, fonction)").fill("Mariam, lingère")
        controle.verifier(agent, "enlèvement")
        passage.get_by_role("button", name="Valider 19 pièces").click()
        expect(agent.locator(".alerte-succes")).to_contain_text("19 pièces enlevées")
        depot = agent.locator(".carte-collecte", has_text=structure).first
        bon = depot.locator(".reference").inner_text()
        depot.get_by_role("button", name="Déposé chez le partenaire").click()
        expect(agent.locator(".alerte-succes")).to_contain_text(f"{bon} : déposée chez Pressing de démonstration")
        agent.goto(f"{ADRESSE}/equipe/tournee?jour={retour_promis(maintenant, 2)}", wait_until="networkidle")
        a_rendre = agent.locator(".carte-collecte", has_text=bon)
        a_rendre.get_by_role("button", name="Rendre et recompter").click()
        a_rendre.get_by_label("Drap").fill("11")
        a_rendre.get_by_label("Reçu par (nom, fonction)").fill("Mariam, lingère")
        controle.verifier(agent, "retour")
        a_rendre.get_by_role("button", name="Valider le retour").click()
        expect(agent.locator(".alerte-succes")).to_contain_text(f"{bon} : rendue, 1 pièce(s) manquante(s)")
        agent.goto(f"{ADRESSE}/equipe/collectes/{bon}", wait_until="networkidle")
        expect(agent.locator(".manquantes")).to_contain_text("1 pièce manquante au retour")
        controle.verifier(agent, "bon de collecte")
        agent.goto(f"{ADRESSE}/equipe/releves", wait_until="networkidle")
        expect(agent.get_by_text("Ce compte n'a pas accès à cet écran.")).to_be_visible()

        # Le relevé du mois : 11 draps à 700, 5 blouses à 500, 2 taies à 250 ; le pressing
        # facture 400, 300 et 150.
        controle.etape = "relevés"
        gestion.goto(f"{ADRESSE}/equipe/releves", wait_until="networkidle")
        ligne = gestion.locator("tr", has_text=contrat)
        expect(ligne).to_contain_text("10 700 FCFA")
        expect(ligne).to_contain_text("6 200 FCFA")
        expect(ligne).to_contain_text("4 500 FCFA")
        with gestion.expect_download() as telechargement:
            ligne.get_by_role("button", name="PDF").click()
        if not telechargement.value.suggested_filename.startswith(f"releve-{contrat}-"):
            controle.erreurs.append("relevés : nom du PDF inattendu")

    for erreur in controle.erreurs:
        print(f"✗ {erreur}")
    print(f"Entretien du linge : demande, contrat {contrat}, bon {bon}, relevé.")
    return 1 if controle.erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
