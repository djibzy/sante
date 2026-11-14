"""Le fil d'une commande tel que le voient le client et l'équipe : messages, propositions,
étapes et paiements, dans l'ordre où ils sont arrivés."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from boutique.messagerie.etats import Auteur, EtatProposition

TEXTE_MAX = 2000


class EntreeFil(BaseModel):
    """Une ligne du fil. Les champs vides ne concernent pas ce type d'entrée."""

    type: Literal["message", "proposition", "etape", "paiement", "remboursement"]
    quand: datetime
    # Message ou proposition
    id: UUID | None = None
    auteur: Auteur | None = None
    nom_auteur: str = Field("", description="Membre de l'équipe ; montré à l'équipe seulement")
    texte: str = ""
    image: bool = Field(False, description="Une image est jointe (à lire par …/image)")
    etat: EtatProposition | None = None
    libelle_etat: str = ""
    repondue_le: datetime | None = None
    lu_le: datetime | None = Field(None, description="Lu par l'autre partie")
    retire: bool = False
    motif_retrait: str = ""
    # Étape (changement de statut), paiement, remboursement
    libelle: str = ""
    note: str = ""
    interne: bool = Field(False, description="Étape que le client ne voit pas")
    montant: int | None = None


class Fil(BaseModel):
    reference: str
    ouvert: bool = Field(description="On peut encore écrire (commande non archivée)")
    entrees: list[EntreeFil]
    a_lire: int = Field(description="Messages de l'autre partie pas encore lus")
    propositions_en_attente: int


class Reponse(BaseModel):
    accepte: bool


class Retrait(BaseModel):
    motif: str = Field(min_length=3, max_length=200)
