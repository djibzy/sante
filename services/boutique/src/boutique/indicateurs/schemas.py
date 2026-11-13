from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Ventes(BaseModel):
    commandes_recues: int = Field(description="Commandes passées sur la période (hors devis)")
    commandes_livrees: int = Field(description="Commandes remises au client sur la période")
    chiffre_affaires: int = Field(description="Total des commandes remises sur la période, FCFA")
    panier_moyen: int | None
    encaisse: int = Field(description="Paiements reçus sur la période, FCFA")
    encaisse_par_moyen: dict[str, int]
    encaisse_en_ligne: int
    rembourse: int = Field(0, description="Rendu aux clients sur la période, FCFA")
    a_encaisser: int = Field(description="Reste dû sur les commandes déjà remises, FCFA")
    annulees: int


class Devis(BaseModel):
    demandes: int
    envoyes: int
    acceptes: int
    refuses: int
    taux_acceptation: float | None = Field(description="Acceptés parmi les devis tranchés (0 à 1)")


class Delais(BaseModel):
    confirmation_heures: float | None = Field(description="De la commande à sa confirmation")
    livraison_jours: float | None = Field(description="De la commande à sa remise au client")
    a_l_heure: float | None = Field(description="Remises au plus tard à la date promise (0 à 1)")


class Clients(BaseModel):
    clients: int = Field(description="Numéros distincts ayant commandé sur la période")
    nouveaux: int = Field(description="Dont première commande sur la période")
    avis_publies: int
    note_moyenne: float | None = Field(description="Tous les avis publiés, sur 5")
    avis_a_relire: int


class VenteProduit(BaseModel):
    produit_slug: str | None
    libelle: str
    quantite: int
    montant: int


class TailleCommandee(BaseModel):
    taille: str
    quantite: int


class TaillesDuProduit(BaseModel):
    """Répartition des tailles d'un article : de quoi couper d'avance et réassortir."""

    produit_slug: str
    libelle: str
    quantite: int
    tailles: list[TailleCommandee]  # XS < S < M … puis les pointures


class CouleurCommandee(BaseModel):
    couleur: str
    couleur_hex: str | None
    quantite: int


class Alertes(BaseModel):
    a_traiter: int = Field(description="Commandes à confirmer et devis demandés")
    acomptes_attendus: int = Field(description="Confirmées, fabrication en attente de l'acompte")
    en_retard: int = Field(description="Date promise dépassée, pas encore remises")
    stock_bas: int
    sms_en_echec: int
    paiements_a_verifier: int
    a_rembourser: int = Field(0, description="Commandes où de l'argent reste à rendre")
    montant_a_rembourser: int = Field(0, description="Total à rendre aux clients, FCFA")


class Point(BaseModel):
    debut: date
    chiffre_affaires: int
    commandes: int


class TableauDeBord(BaseModel):
    du: date
    au: date
    ventes: Ventes
    devis: Devis
    delais: Delais
    clients: Clients
    meilleures_ventes: list[VenteProduit]
    tailles: list[TaillesDuProduit] = Field(
        default_factory=list, description="Commandes passées sur la période, hors annulées"
    )
    couleurs: list[CouleurCommandee] = Field(default_factory=list)
    alertes: Alertes
    pas: Literal["jour", "semaine"]
    serie: list[Point] = Field(description="Chiffre d'affaires remis, par jour ou par semaine")
