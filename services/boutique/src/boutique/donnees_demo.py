"""Catalogue de démonstration, pour la préproduction et les essais.

    uv run python -m boutique.donnees_demo

Idempotent : un rayon ou un produit déjà présent (même slug) n'est pas recréé. Les prix sont
les hypothèses du modèle financier (tenue 15 000, imprimé 3 500, kit 12 500 FCFA en moyenne) :
à remplacer par la vraie grille avant l'ouverture.
"""

import asyncio
from typing import Any

from sqlalchemy import select

from boutique.config import ParametresBoutique
from boutique.models import CATEGORIE_PHARMACEUTIQUE, Produit, Rayon, Variante, ZoneLivraison
from socle.db import creer_moteur, fabrique_sessions

TAILLES = ("S", "M", "L", "XL")

RAYONS: list[dict[str, Any]] = [
    {
        "slug": "tenues-brodees",
        "nom": "Tenues brodées",
        "position": 1,
        "description": "Blouses, tuniques, pantalons et calots brodés au nom, à la fonction "
        "et au logo de votre structure.",
    },
    {
        "slug": "textiles-imprimes",
        "nom": "Textiles et imprimés",
        "position": 2,
        "description": "T-shirts, casquettes, affiches et boîtes à images pour vos campagnes.",
    },
    {
        "slug": "kits",
        "nom": "Kits assemblés",
        "position": 3,
        "description": "Kits d'hygiène, de premiers secours et du relais, composés article par "
        "article.",
    },
    {
        "slug": "produits-medicaux",
        "nom": "Produits médicaux",
        "position": 4,
        "description": "Consommables et petit matériel. Les articles réservés au pharmacien "
        "sont délivrés par notre pharmacien partenaire.",
    },
    {
        "slug": "accessoires",
        "nom": "Ce qui va avec",
        "position": 5,
        "description": "Badges, porte-noms, trousses et chaussures de travail.",
    },
]


def _produit(
    slug: str,
    nom: str,
    rayon: str,
    resume: str,
    prix: int | None,
    prix_pro: int | None = None,
    *,
    personnalisable: bool = False,
    tailles: tuple[str, ...] = (),
    couleur: str | None = None,
    pharmaceutique: bool = False,
    delai: int = 7,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "nom": nom,
        "rayon": rayon,
        "resume": resume,
        "prix_public": prix,
        "prix_pro": prix_pro,
        "personnalisable": personnalisable,
        "tailles": tailles,
        "couleur": couleur,
        "pharmaceutique": pharmaceutique,
        "delai": delai,
    }


PRODUITS: list[dict[str, Any]] = [
    _produit(
        "blouse-medicale-brodee",
        "Blouse médicale brodée",
        "tenues-brodees",
        "Coton épais, nom et fonction brodés sur la poitrine.",
        12500,
        11000,
        personnalisable=True,
        tailles=TAILLES,
        couleur="Blanc",
        delai=10,
    ),
    _produit(
        "tenue-de-bloc-brodee",
        "Tenue de bloc brodée",
        "tenues-brodees",
        "Tunique et pantalon, logo de la structure brodé.",
        15000,
        13500,
        personnalisable=True,
        tailles=TAILLES,
        couleur="Vert bloc",
        delai=10,
    ),
    _produit(
        "tunique-sage-femme",
        "Tunique de sage-femme brodée",
        "tenues-brodees",
        "Tunique cintrée, broderie au choix.",
        14000,
        12500,
        personnalisable=True,
        tailles=TAILLES,
        couleur="Rose",
        delai=10,
    ),
    _produit(
        "calot-brode",
        "Calot brodé",
        "tenues-brodees",
        "Calot en coton, prénom ou logo brodé.",
        3000,
        2500,
        personnalisable=True,
    ),
    _produit(
        "tshirt-de-campagne",
        "T-shirt de campagne imprimé",
        "textiles-imprimes",
        "Votre message et vos logos, en grande série.",
        3500,
        3000,
        personnalisable=True,
        tailles=TAILLES,
        couleur="Blanc",
        delai=14,
    ),
    _produit(
        "casquette-imprimee",
        "Casquette imprimée",
        "textiles-imprimes",
        "Casquette à visière, impression du message de campagne.",
        2500,
        2000,
        personnalisable=True,
        delai=14,
    ),
    _produit(
        "affiche-a2",
        "Affiche de sensibilisation A2",
        "textiles-imprimes",
        "Affiche conçue par le studio, validée par le comité médical.",
        1500,
        1200,
    ),
    _produit(
        "boite-a-images",
        "Boîte à images pour causeries",
        "textiles-imprimes",
        "L'outil des relais pour animer les causeries, en images et en bambara.",
        12000,
        10000,
        delai=14,
    ),
    _produit(
        "kit-hygiene",
        "Kit hygiène et lavage des mains",
        "kits",
        "Savon, bouilloire, serviettes et fiche illustrée.",
        7500,
        6500,
    ),
    _produit(
        "kit-du-relais",
        "Kit du relais communautaire",
        "kits",
        "Sac, gilet, boîte à images, carnet et lampe solaire.",
        18000,
        16000,
        delai=14,
    ),
    _produit(
        "kit-premiers-secours",
        "Kit de premiers secours sans médicament",
        "kits",
        "Pansements non stériles, bandes, ciseaux, couverture de survie.",
        12500,
        11000,
    ),
    _produit(
        "thermometre-digital",
        "Thermomètre digital",
        "produits-medicaux",
        "Lecture en 10 secondes, pile fournie.",
        3000,
        2500,
    ),
    _produit(
        "tensiometre-electronique",
        "Tensiomètre électronique",
        "produits-medicaux",
        "Mesure au bras, mémoire de 60 mesures.",
        25000,
        22000,
    ),
    _produit(
        "gants-steriles",
        "Gants stériles",
        "produits-medicaux",
        "Délivrés par notre pharmacien partenaire.",
        None,
        pharmaceutique=True,
    ),
    _produit(
        "tests-de-grossesse",
        "Tests de grossesse",
        "produits-medicaux",
        "Délivrés par notre pharmacien partenaire.",
        None,
        pharmaceutique=True,
    ),
    _produit(
        "badge-porte-nom",
        "Badge porte-nom gravé",
        "accessoires",
        "Nom et fonction gravés, attache aimantée.",
        2000,
        1500,
        personnalisable=True,
    ),
    _produit(
        "trousse-du-soignant",
        "Trousse du soignant",
        "accessoires",
        "Trousse de poche pour stylos, ciseaux et lampe.",
        4500,
        4000,
    ),
    _produit(
        "sabots-de-travail",
        "Sabots de travail",
        "accessoires",
        "Sabots antidérapants, faciles à laver.",
        9000,
        8000,
        tailles=("37", "38", "39", "40", "41", "42", "43", "44"),
    ),
]


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
                rayon_id=par_slug[d["rayon"]].id,
                categorie_reglementaire=CATEGORIE_PHARMACEUTIQUE
                if d["pharmaceutique"]
                else "libre",
                personnalisable=d["personnalisable"],
                prix_public=d["prix_public"],
                prix_pro=d["prix_pro"],
                delai_jours=d["delai"],
            )
            produit.variantes = [
                Variante(
                    sku=f"{d['slug']}-{taille}".upper(),
                    libelle=f"Taille {taille}" + (f" · {d['couleur']}" if d["couleur"] else ""),
                    taille=taille,
                    couleur=d["couleur"],
                    position=i,
                )
                for i, taille in enumerate(d["tailles"])
            ]
            session.add(produit)
            produits_crees += 1

        zones = set((await session.execute(select(ZoneLivraison.slug))).scalars())
        session.add_all(ZoneLivraison(**z) for z in ZONES if z["slug"] not in zones)
        await session.commit()
    await moteur.dispose()
    return rayons_crees, produits_crees


if __name__ == "__main__":
    rayons, produits = asyncio.run(charger())
    print(f"Données de démonstration : {rayons} rayons et {produits} produits ajoutés.")
