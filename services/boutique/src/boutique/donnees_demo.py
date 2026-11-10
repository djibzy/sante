"""Catalogue de démonstration, pour la préproduction et les essais.

    uv run python -m boutique.donnees_demo

Idempotent : un rayon ou un produit déjà présent (même slug) n'est pas recréé. Les prix sont
les hypothèses du modèle financier (tenue 15 000, imprimé 3 500, kit 12 500 FCFA en moyenne) :
à remplacer par la vraie grille avant l'ouverture.
"""

import asyncio
import unicodedata
from typing import Any

from sqlalchemy import select

from boutique.config import ParametresBoutique
from boutique.models import CATEGORIE_PHARMACEUTIQUE, Produit, Rayon, Variante, ZoneLivraison
from socle.db import creer_moteur, fabrique_sessions

TAILLES = ("XS", "S", "M", "L", "XL", "XXL")
POINTURES = tuple(str(p) for p in range(36, 46))

BLANC = ("Blanc", "#ffffff")
BLEU_CIEL = ("Bleu ciel", "#9fc9ea")
ROSE_POUDRE = ("Rose poudré", "#e8b4b8")
BLEU_ROI = ("Bleu roi", "#1f4fa8")
VERT_BLOC = ("Vert bloc", "#2e8b6e")
BORDEAUX = ("Bordeaux", "#7a1f35")
ARDOISE = ("Gris ardoise", "#5b6770")
MARINE = ("Bleu marine", "#1c2a4a")
TURQUOISE = ("Turquoise", "#1aa6a6")
PRUNE = ("Prune", "#6b2d5c")
VERT_EAU = ("Vert d'eau", "#9fd8c8")
NOIR = ("Noir", "#1d1d1f")
GRIS_CHINE = ("Gris chiné", "#9a9ea6")
WAX_BLEU = ("Wax bleu", "#2b5fb3")
WAX_ORANGE = ("Wax orange", "#e07b1f")

POLYCOTON = "Polycoton 65 % polyester, 35 % coton, 210 g/m²"
STRETCH = "Polyester, viscose et élasthanne, extensible dans les quatre sens"
LAVAGE = "Lavage à 60 °C, séchage rapide, repassage doux"

RAYONS: list[dict[str, Any]] = [
    {
        "slug": "blouses-medicales",
        "nom": "Blouses médicales",
        "univers": "tenues",
        "position": 1,
        "description": "Blouses femme, homme et mixtes, pour tous les métiers, brodées à "
        "votre nom.",
    },
    {
        "slug": "tuniques",
        "nom": "Tuniques médicales",
        "univers": "tenues",
        "position": 2,
        "description": "Tuniques col V et cintrées, en couleurs unies ou à empiècements wax.",
    },
    {
        "slug": "pantalons",
        "nom": "Pantalons médicaux",
        "univers": "tenues",
        "position": 3,
        "description": "Pantalons unisexes, stretch ou cargo, assortis aux tuniques.",
    },
    {
        "slug": "tenues-de-bloc",
        "nom": "Tenues de bloc",
        "univers": "tenues",
        "position": 4,
        "description": "Tenues de bloc complètes et calots, brodés au logo de votre structure.",
    },
    {
        "slug": "chaussures",
        "nom": "Chaussures médicales",
        "univers": "tenues",
        "position": 5,
        "description": "Sabots et baskets antidérapants, faciles à laver.",
    },
    {
        "slug": "gilets-polos",
        "nom": "Gilets et polos",
        "univers": "tenues",
        "position": 6,
        "description": "Gilets zippés et polos brodés pour les gardes et l'accueil.",
    },
    {
        "slug": "accessoires",
        "nom": "Accessoires du soignant",
        "univers": "tenues",
        "position": 7,
        "description": "Badges gravés, trousses de poche, montres d'infirmière.",
    },
    {
        "slug": "kits",
        "nom": "Kits de soins",
        "univers": "equipement",
        "position": 8,
        "description": "Kits d'hygiène, de premiers secours et du relais communautaire, "
        "composés article par article.",
    },
    {
        "slug": "materiel-medical",
        "nom": "Matériel médical",
        "univers": "equipement",
        "position": 9,
        "description": "Thermomètres et tensiomètres ; les articles du domaine "
        "pharmaceutique passent par notre pharmacien partenaire.",
    },
    {
        "slug": "campagnes",
        "nom": "Campagnes de sensibilisation",
        "univers": "campagnes",
        "position": 10,
        "description": "T-shirts, casquettes, affiches et boîtes à images pour vos "
        "campagnes, conçus avec notre studio.",
    },
]


def _produit(
    slug: str, nom: str, rayon: str, resume: str, prix: int | None, pro: int | None, **autres: Any
) -> dict[str, Any]:
    return {
        "slug": slug,
        "nom": nom,
        "rayon": rayon,
        "resume": resume,
        "prix_public": prix,
        "prix_pro": pro,
        "description": "",
        "tailles": (),
        "couleurs": (),
        "delai": 7,
        "personnalisable": False,
        "pharmaceutique": False,
        "metiers": [],
        "genre": None,
        "manches": None,
        "collection": None,
        "matiere": "",
        "entretien": "",
        "est_nouveau": False,
        "prix_avant_promo": None,
        **autres,
    }


TOUS = ["infirmier", "sage-femme", "medecin", "aide-soignant"]
PRODUITS: list[dict[str, Any]] = [
    # Blouses médicales
    _produit("blouse-medicale-brodee", "Blouse médicale brodée", "blouses-medicales",
             "Coton épais, nom et fonction brodés sur la poitrine.", 12_500, 11_000,
             tailles=("S", "M", "L", "XL", "XXL"), couleurs=(BLANC,), delai=10,
             personnalisable=True, metiers=["infirmier", "medecin", "laboratoire", "etudiant"],
             genre="mixte", manches="courtes", collection="Essentielle", matiere=POLYCOTON,
             entretien=LAVAGE, description="La blouse de tous les jours : trois poches, fente "
             "dos, boutons pression. Votre nom et votre fonction brodés sur la poitrine."),
    _produit("blouse-femme-cintree", "Blouse femme cintrée", "blouses-medicales",
             "Coupe cintrée, col cranté, deux poches basses et une poche poitrine.", 14_000,
             12_500, tailles=TAILLES, couleurs=(BLANC, BLEU_CIEL, ROSE_POUDRE), delai=10,
             personnalisable=True, metiers=["infirmier", "sage-femme", "pharmacie",
             "laboratoire"], genre="femme", manches="courtes", collection="Essentielle",
             matiere=POLYCOTON, entretien=LAVAGE, est_nouveau=True),
    _produit("blouse-homme-col-officier", "Blouse homme col officier", "blouses-medicales",
             "Col officier, fermeture pression, longueur genou.", 15_000, 13_500,
             tailles=("M", "L", "XL", "XXL", "XXXL"), couleurs=(BLANC,), delai=10,
             personnalisable=True, metiers=["medecin", "pharmacie", "dentiste"], genre="homme",
             manches="longues", collection="Essentielle", matiere=POLYCOTON, entretien=LAVAGE),
    _produit("blouse-pharmacie-zippee", "Blouse de pharmacie zippée", "blouses-medicales",
             "Fermeture éclair, poches stylos, tissu déperlant.", 13_000, 11_500,
             tailles=TAILLES, couleurs=(BLANC, VERT_EAU), delai=10, personnalisable=True,
             metiers=["pharmacie"], genre="mixte", manches="courtes", matiere=POLYCOTON,
             entretien=LAVAGE, prix_avant_promo=15_000),
    _produit("blouse-de-stage", "Blouse de stage étudiant", "blouses-medicales",
             "Robuste et économique, pour les stages hospitaliers.", 9_000, 8_000,
             tailles=("XS", "S", "M", "L", "XL"), couleurs=(BLANC,), delai=10,
             personnalisable=True, metiers=["etudiant", "laboratoire"], genre="mixte",
             manches="longues", collection="Essentielle", matiere=POLYCOTON, entretien=LAVAGE),
    # Tuniques
    _produit("tunique-sage-femme", "Tunique de sage-femme brodée", "tuniques",
             "Tunique cintrée, broderie au choix.", 14_000, 12_500,
             tailles=("S", "M", "L", "XL"), couleurs=(("Rose", "#e58fa5"),), delai=10,
             personnalisable=True, metiers=["sage-femme"], genre="femme", manches="courtes",
             matiere=POLYCOTON, entretien=LAVAGE),
    _produit("tunique-col-v", "Tunique col V unisexe", "tuniques",
             "La tunique de garde : col V, trois poches, couleurs par service.", 9_500, 8_500,
             tailles=TAILLES, couleurs=(BLEU_ROI, VERT_BLOC, BORDEAUX, ARDOISE), delai=10,
             personnalisable=True, metiers=[*TOUS, "dentiste"], genre="mixte",
             manches="courtes", collection="Essentielle", matiere=POLYCOTON, entretien=LAVAGE),
    _produit("tunique-stretch-femme", "Tunique stretch femme", "tuniques",
             "Extensible, légère, elle suit chaque mouvement pendant les longues gardes.",
             12_000, 10_500, tailles=TAILLES, couleurs=(MARINE, TURQUOISE, PRUNE), delai=10,
             personnalisable=True, metiers=["infirmier", "sage-femme", "aide-soignant"],
             genre="femme", manches="courtes", collection="Confort stretch", matiere=STRETCH,
             entretien="Lavage à 40 °C, séchage à l'air libre", est_nouveau=True),
    _produit("tunique-wax", "Tunique à empiècements wax", "tuniques",
             "Empiècements en wax sur les épaules et les poches, tissu technique au corps.",
             13_500, 12_000, tailles=("S", "M", "L", "XL", "XXL"),
             couleurs=(WAX_BLEU, WAX_ORANGE), delai=14, personnalisable=True,
             metiers=["sage-femme", "infirmier", "aide-soignant"], genre="mixte",
             manches="courtes", collection="Wax", matiere=POLYCOTON + ", empiècements wax",
             entretien="Lavage à 40 °C à l'envers", est_nouveau=True),
    # Pantalons
    _produit("pantalon-unisexe", "Pantalon médical unisexe", "pantalons",
             "Taille élastiquée avec cordon, deux poches, assorti aux tuniques.", 7_500, 6_500,
             tailles=TAILLES, couleurs=(BLANC, BLEU_ROI, VERT_BLOC), metiers=TOUS,
             genre="mixte", collection="Essentielle", matiere=POLYCOTON, entretien=LAVAGE),
    _produit("pantalon-stretch-femme", "Pantalon stretch femme", "pantalons",
             "Coupe droite, ceinture confortable, tissu extensible.", 9_000, 8_000,
             tailles=TAILLES, couleurs=(BLANC, MARINE), metiers=TOUS, genre="femme",
             collection="Confort stretch", matiere=STRETCH, entretien="Lavage à 40 °C",
             est_nouveau=True),
    _produit("pantalon-cargo-homme", "Pantalon cargo homme", "pantalons",
             "Six poches, genoux renforcés, pour les métiers qui bougent.", 9_500, 8_500,
             tailles=("S", "M", "L", "XL", "XXL", "XXXL"), couleurs=(BLANC, ARDOISE),
             metiers=["infirmier", "aide-soignant", "laboratoire"], genre="homme",
             matiere=POLYCOTON, entretien=LAVAGE),
    # Tenues de bloc
    _produit("tenue-de-bloc-brodee", "Tenue de bloc brodée", "tenues-de-bloc",
             "Tunique et pantalon, logo de la structure brodé.", 15_000, 13_500,
             tailles=("S", "M", "L", "XL"), couleurs=(("Vert bloc", "#2e8b6e"),), delai=10,
             personnalisable=True, metiers=["medecin", "infirmier"], genre="mixte",
             manches="courtes", matiere=POLYCOTON, entretien="Lavage à 90 °C possible"),
    _produit("calot-brode", "Calot brodé", "tenues-de-bloc",
             "Calot en coton, prénom ou logo brodé.", 3_000, 2_500, personnalisable=True,
             metiers=["medecin", "infirmier"], genre="mixte"),
    _produit("calot-wax", "Calot en tissu wax", "tenues-de-bloc",
             "Calot noué, en wax doublé de coton.", 2_500, 2_000,
             couleurs=(WAX_BLEU, WAX_ORANGE), metiers=["medecin", "infirmier", "dentiste"],
             genre="mixte", collection="Wax", est_nouveau=True),
    # Chaussures
    _produit("sabots-de-travail", "Sabots de travail", "chaussures",
             "Sabots antidérapants, faciles à laver.", 9_000, 8_000,
             tailles=("37", "38", "39", "40", "41", "42", "43", "44"), metiers=TOUS,
             genre="mixte"),
    _produit("baskets-soignant", "Baskets légères du soignant", "chaussures",
             "Semelle antidérapante, dessus lavable, maintien du talon.", 15_000, 13_500,
             tailles=POINTURES, couleurs=(BLANC, NOIR), metiers=TOUS, genre="mixte",
             est_nouveau=True),
    # Gilets et polos
    _produit("gilet-zippe", "Gilet zippé du soignant", "gilets-polos",
             "Molleton léger, pour les gardes de nuit et les salles climatisées.", 9_000, 8_000,
             tailles=TAILLES, couleurs=(MARINE, GRIS_CHINE), metiers=TOUS, genre="mixte"),
    _produit("polo-brode", "Polo brodé", "gilets-polos",
             "Polo piqué, logo ou nom brodé, pour l'accueil et les équipes.", 6_500, 5_500,
             tailles=TAILLES, couleurs=(BLANC, BLEU_ROI), delai=10, personnalisable=True,
             metiers=["pharmacie", "laboratoire", "aide-soignant"], genre="mixte",
             manches="courtes", matiere="Coton piqué 220 g/m²", entretien="Lavage à 40 °C"),
    # Accessoires
    _produit("badge-porte-nom", "Badge porte-nom gravé", "accessoires",
             "Nom et fonction gravés, attache aimantée.", 2_000, 1_500, personnalisable=True,
             metiers=TOUS),
    _produit("trousse-du-soignant", "Trousse du soignant", "accessoires",
             "Trousse de poche pour stylos, ciseaux et lampe.", 4_500, 4_000, metiers=TOUS),
    _produit("montre-infirmiere", "Montre de poche infirmière", "accessoires",
             "Montre à clip, cadran inversé, lavable.", 3_500, 3_000,
             couleurs=(BLEU_ROI, ROSE_POUDRE), metiers=["infirmier", "sage-femme"]),
    # Kits
    _produit("kit-hygiene", "Kit hygiène et lavage des mains", "kits",
             "Savon, bouilloire, serviettes et fiche illustrée.", 7_500, 6_500),
    _produit("kit-du-relais", "Kit du relais communautaire", "kits",
             "Sac, gilet, boîte à images, carnet et lampe solaire.", 18_000, 16_000, delai=14),
    _produit("kit-premiers-secours", "Kit de premiers secours sans médicament", "kits",
             "Pansements non stériles, bandes, ciseaux, couverture de survie.", 12_500, 11_000),
    # Matériel médical
    _produit("thermometre-digital", "Thermomètre digital", "materiel-medical",
             "Lecture en 10 secondes, pile fournie.", 3_000, 2_500),
    _produit("tensiometre-electronique", "Tensiomètre électronique", "materiel-medical",
             "Mesure au bras, mémoire de 60 mesures.", 25_000, 22_000),
    _produit("gants-steriles", "Gants stériles", "materiel-medical",
             "Délivrés par notre pharmacien partenaire.", None, None, pharmaceutique=True),
    _produit("tests-de-grossesse", "Tests de grossesse", "materiel-medical",
             "Délivrés par notre pharmacien partenaire.", None, None, pharmaceutique=True),
    # Campagnes de sensibilisation
    _produit("tshirt-de-campagne", "T-shirt de campagne imprimé", "campagnes",
             "Votre message et vos logos, en grande série.", 3_500, 3_000,
             tailles=("S", "M", "L", "XL"), couleurs=(BLANC,), delai=14, personnalisable=True),
    _produit("casquette-imprimee", "Casquette imprimée", "campagnes",
             "Casquette à visière, impression du message de campagne.", 2_500, 2_000, delai=14,
             personnalisable=True),
    _produit("affiche-a2", "Affiche de sensibilisation A2", "campagnes",
             "Affiche conçue par le studio, validée par le comité médical.", 1_500, 1_200),
    _produit("boite-a-images", "Boîte à images pour causeries", "campagnes",
             "L'outil des relais pour animer les causeries, en images et en langues locales.",
             12_000, 10_000, delai=14),
]  # fmt: skip

TEXTILES = {"blouses-medicales", "tuniques", "tenues-de-bloc", "gilets-polos"}
POSTES_PRODUITS = {"badge-porte-nom": "impression"}


def poste(donnees: dict[str, Any]) -> str | None:
    """Brodé à l'atelier, imprimé, assemblé en kit ; sinon vendu tel quel, suivi en stock."""
    if donnees["slug"] in POSTES_PRODUITS:
        return POSTES_PRODUITS[donnees["slug"]]
    if donnees["rayon"] == "campagnes":
        return "impression"
    if donnees["rayon"] == "kits":
        return "assemblage"
    if donnees["personnalisable"] and donnees["rayon"] in TEXTILES:
        return "broderie"
    return None


def _code(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return "-".join(sans_accents.upper().replace("'", " ").split())


def variantes(d: dict[str, Any]) -> list[Variante]:
    """Une variante par couleur et par taille ; le code garde l'ancien format pour les
    produits d'une seule couleur."""
    tailles = d["tailles"] or (None,)
    couleurs = d["couleurs"] or ((None, None),)
    mot = "Pointure" if d["rayon"] == "chaussures" else "Taille"
    resultat: list[Variante] = []
    for (couleur, teinte), taille in ((c, t) for c in couleurs for t in tailles):
        if couleur is None and taille is None:
            return []
        morceaux = [d["slug"]]
        if couleur and len(couleurs) > 1:
            morceaux.append(_code(couleur))
        if taille:
            morceaux.append(taille)
        libelle = " · ".join(x for x in (f"{mot} {taille}" if taille else None, couleur) if x)
        resultat.append(
            Variante(
                sku="-".join(morceaux).upper(),
                libelle=libelle,
                taille=taille,
                couleur=couleur,
                couleur_hex=teinte,
                position=len(resultat),
            )
        )
    return resultat


# Frais de livraison hypothétiques, à remplacer par les tarifs réels du livreur.
ZONES: list[dict[str, Any]] = [
    *(
        {
            "slug": f"bamako-commune-{n}",
            "nom": f"Bamako, commune {r}",
            "frais": 1000,
            "delai_jours": 1,
            "position": n,
        }
        for n, r in enumerate(("I", "II", "III", "IV", "V", "VI"), start=1)
    ),
    {"slug": "kati", "nom": "Kati", "frais": 2000, "delai_jours": 2, "position": 7},
    {"slug": "kalaban-coro", "nom": "Kalaban Coro", "frais": 1500, "delai_jours": 2, "position": 8},
]


async def charger(database_url: str | None = None) -> tuple[int, int]:
    """Ajoute les rayons, produits et zones manquants ; renvoie le nombre de rayons et de
    produits créés."""
    moteur = creer_moteur(database_url or ParametresBoutique().database_url, pool=False)
    rayons_crees = produits_crees = 0
    async with fabrique_sessions(moteur)() as session:
        par_slug: dict[str, Rayon] = {
            r.slug: r for r in (await session.execute(select(Rayon))).scalars()
        }
        for donnees in RAYONS:
            if donnees["slug"] not in par_slug:
                rayon = Rayon(**donnees)
                session.add(rayon)
                par_slug[rayon.slug] = rayon
                rayons_crees += 1
        await session.flush()

        existants = set((await session.execute(select(Produit.slug))).scalars())
        for d in PRODUITS:
            if d["slug"] in existants:
                continue
            produit = Produit(
                slug=d["slug"],
                nom=d["nom"],
                resume=d["resume"],
                description=d["description"],
                rayon_id=par_slug[d["rayon"]].id,
                categorie_reglementaire=CATEGORIE_PHARMACEUTIQUE
                if d["pharmaceutique"]
                else "libre",
                personnalisable=d["personnalisable"],
                prix_public=d["prix_public"],
                prix_pro=d["prix_pro"],
                prix_avant_promo=d["prix_avant_promo"],
                delai_jours=d["delai"],
                poste_atelier=poste(d),
                metiers=d["metiers"],
                genre=d["genre"],
                manches=d["manches"],
                collection=d["collection"],
                matiere=d["matiere"],
                entretien=d["entretien"],
                est_nouveau=d["est_nouveau"],
            )
            produit.variantes = variantes(d)
            session.add(produit)
            produits_crees += 1

        # Produits de démonstration créés avant l'atelier : on leur attribue leur poste.
        sans_poste = await session.scalars(select(Produit).where(Produit.poste_atelier.is_(None)))
        par_slug_produit = {d["slug"]: d for d in PRODUITS}
        for produit in sans_poste:
            if produit.slug in par_slug_produit:
                produit.poste_atelier = poste(par_slug_produit[produit.slug])

        zones = set((await session.execute(select(ZoneLivraison.slug))).scalars())
        session.add_all(ZoneLivraison(**z) for z in ZONES if z["slug"] not in zones)
        await session.commit()
    await moteur.dispose()
    return rayons_crees, produits_crees


if __name__ == "__main__":
    rayons, produits = asyncio.run(charger())
    print(f"Données de démonstration : {rayons} rayons et {produits} produits ajoutés.")
