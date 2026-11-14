"""Données de démonstration, pour essayer les écrans en local : deux partenaires fictifs, deux
contrats (à la pièce et au forfait) qui couvrent la semaine du lundi au samedi, une demande.
Les tarifs sont des exemples, sans valeur commerciale. Refusé en production.

    uv run python -m prestations.donnees_demo
"""

import asyncio
from datetime import date

from sqlalchemy import func, select

from prestations.config import ParametresPrestations
from prestations.etats import Formule, ModeTarif, StatutContrat, TypePartenaire
from prestations.linge import Service, TypeStructure
from prestations.models import Contrat, Demande, Partenaire
from socle.db import creer_moteur, fabrique_sessions


async def charger(database_url: str | None = None) -> int:
    """Ajoute les données si la base n'a encore aucun partenaire ; renvoie le nombre d'objets
    créés."""
    parametres = ParametresPrestations()
    if parametres.en_production:
        raise SystemExit("Données de démonstration refusées en production")
    moteur = creer_moteur(database_url or parametres.database_url, pool=False)
    crees = 0
    async with fabrique_sessions(moteur)() as session:
        if await session.scalar(select(func.count(Partenaire.id))):
            await moteur.dispose()
            return 0
        pressing = Partenaire(
            nom="Pressing de démonstration",
            type=TypePartenaire.PRESSING,
            contact="Responsable du pressing",
            telephone="+22370000101",
            quartier="Hamdallaye, Bamako",
            delai_jours=2,
            mode_tarif=ModeTarif.PIECE,
            tarifs={"blouse": 300, "tunique": 250, "pantalon": 250, "drap": 400, "taie": 150},
            notes="Partenaire fictif : tarifs d'exemple.",
        )
        blanchisserie = Partenaire(
            nom="Blanchisserie de démonstration",
            type=TypePartenaire.BLANCHISSERIE,
            contact="Responsable de la blanchisserie",
            telephone="+22370000102",
            quartier="Zone industrielle, Bamako",
            delai_jours=1,
            capacite_pieces_jour=400,
            mode_tarif=ModeTarif.KG,
            tarif_kg=600,
            notes="Partenaire fictif : tarif d'exemple.",
        )
        session.add_all([pressing, blanchisserie])
        await session.flush()
        session.add_all(
            [
                Contrat(
                    service=Service.ENTRETIEN_LINGE,
                    statut=StatutContrat.ACTIF,
                    structure="Clinique de démonstration",
                    type_structure=TypeStructure.CLINIQUE,
                    contact="Surveillante générale",
                    telephone="+22370000201",
                    adresse="Badalabougou, rue 100, porte 10 : entrée du personnel",
                    partenaire_id=pressing.id,
                    jours_collecte=[1, 3, 5],
                    delai_retour_jours=2,
                    formule=Formule.PIECE,
                    tarifs={
                        "blouse": 500,
                        "tunique": 450,
                        "pantalon": 450,
                        "drap": 700,
                        "taie": 250,
                    },
                    debut_le=date(2026, 11, 2),
                    notes="Contrat fictif : tarifs d'exemple.",
                ),  # fmt: skip
                Contrat(
                    service=Service.ENTRETIEN_LINGE,
                    statut=StatutContrat.ACTIF,
                    structure="Maternité de démonstration",
                    type_structure=TypeStructure.MATERNITE,
                    contact="Major de la maternité",
                    telephone="+22370000202",
                    adresse="Kalaban Coura, près du marché : bâtiment B",
                    partenaire_id=blanchisserie.id,
                    jours_collecte=[2, 4, 6],
                    delai_retour_jours=2,
                    formule=Formule.FORFAIT,
                    forfait_mensuel=150_000,
                    pieces_incluses=600,
                    prix_piece_supplementaire=300,
                    debut_le=date(2026, 11, 2),
                    notes="Contrat fictif : forfait d'exemple.",
                ),
            ]
        )
        session.add(
            Demande(
                service=Service.ENTRETIEN_LINGE,
                structure="Cabinet de démonstration",
                type_structure=TypeStructure.CABINET,
                contact="Secrétaire médicale",
                telephone="+22370000301",
                quartier="ACI 2000, Bamako",
                volumes={"blouse": 15, "serviette": 20},
                collectes_par_semaine=1,
                message="Demande fictive.",
            )
        )
        crees = 5
        await session.commit()
    await moteur.dispose()
    return crees


if __name__ == "__main__":
    print(f"Données de démonstration : {asyncio.run(charger())} objets ajoutés.")
