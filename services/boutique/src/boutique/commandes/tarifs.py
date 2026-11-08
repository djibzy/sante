"""Prix d'un panier, calculés par le serveur à partir du catalogue en vigueur.

Le navigateur n'envoie que des identifiants et des quantités : aucun prix venant du client
n'est jamais repris, sauf ceux qu'un membre de l'équipe fixe dans un devis.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.commandes.cycle import ModeLivraison
from boutique.models import Produit, Variante, ZoneLivraison

PHARMACIEN = "délivré par notre pharmacien partenaire, il ne peut pas être commandé en ligne"
INDISPONIBLE = "ce produit n'est plus disponible"
VARIANTE_REQUISE = "choisissez une taille ou une variante"
VARIANTE_INDISPONIBLE = "cette variante n'est plus disponible"


@dataclass(frozen=True)
class Demande:
    produit_id: UUID
    variante_id: UUID | None
    quantite: int
    personnalisation: str | None = None


@dataclass(frozen=True)
class LigneTarifee:
    produit_id: UUID
    variante_id: UUID | None
    produit_slug: str | None
    libelle: str
    sku: str | None
    quantite: int
    prix_unitaire: int | None
    personnalisation: str | None
    delai_jours: int
    poste: str | None = None  # poste de l'atelier qui fabrique l'article
    motif: str | None = None  # renseigné quand la ligne ne peut pas être commandée

    @property
    def commandable(self) -> bool:
        return self.motif is None

    @property
    def montant(self) -> int:
        return (self.prix_unitaire or 0) * self.quantite if self.commandable else 0


def aujourd_hui() -> date:
    return datetime.now(UTC).date()  # le Mali est à l'heure UTC toute l'année


def libelle(produit: Produit, variante: Variante | None) -> str:
    return f"{produit.nom} – {variante.libelle}" if variante else produit.nom


def prix_catalogue(produit: Produit, variante: Variante | None, professionnel: bool) -> int | None:
    """Prix professionnel s'il existe et que l'acheteur y a droit, sinon prix de la variante,
    sinon prix public. Aucun prix pour un article du domaine pharmaceutique."""
    if not produit.vendable_en_ligne:
        return None
    if professionnel and produit.prix_pro is not None:
        return produit.prix_pro
    if variante is not None and variante.prix is not None:
        return variante.prix
    return produit.prix_public


async def charger_produits(session: AsyncSession, ids: Iterable[UUID]) -> dict[UUID, Produit]:
    requete = (
        select(Produit).options(selectinload(Produit.variantes)).where(Produit.id.in_(set(ids)))
    )
    return {p.id: p for p in (await session.execute(requete)).scalars()}


def tarifer_ligne(demande: Demande, produit: Produit | None, professionnel: bool) -> LigneTarifee:
    if produit is None or not produit.est_actif:
        return LigneTarifee(
            produit_id=demande.produit_id,
            variante_id=demande.variante_id,
            produit_slug=produit.slug if produit else None,
            libelle=produit.nom if produit else "Produit inconnu",
            sku=None,
            quantite=demande.quantite,
            prix_unitaire=None,
            personnalisation=None,
            delai_jours=0,
            motif=INDISPONIBLE,
        )
    actives = [v for v in produit.variantes if v.est_active]
    variante = next((v for v in produit.variantes if v.id == demande.variante_id), None)
    motif = None
    if not produit.vendable_en_ligne:
        motif = PHARMACIEN
    elif demande.variante_id is None and actives:
        motif = VARIANTE_REQUISE
    elif demande.variante_id is not None and (variante is None or not variante.est_active):
        motif = VARIANTE_INDISPONIBLE
    personnalisation = (demande.personnalisation or "").strip() or None
    return LigneTarifee(
        produit_id=produit.id,
        variante_id=variante.id if variante else None,
        produit_slug=produit.slug,
        libelle=libelle(produit, variante),
        sku=variante.sku if variante else None,
        quantite=demande.quantite,
        prix_unitaire=prix_catalogue(produit, variante, professionnel),
        personnalisation=personnalisation if produit.personnalisable else None,
        delai_jours=produit.delai_jours,
        poste=produit.poste_atelier,
        motif=motif,
    )


async def tarifer(
    session: AsyncSession, demandes: Sequence[Demande], professionnel: bool
) -> list[LigneTarifee]:
    produits = await charger_produits(session, (d.produit_id for d in demandes))
    return [tarifer_ligne(d, produits.get(d.produit_id), professionnel) for d in demandes]


def frais_de_livraison(mode: ModeLivraison, zone: ZoneLivraison | None) -> int:
    return zone.frais if mode == ModeLivraison.LIVRAISON and zone is not None else 0


def jours_de_transport(mode: ModeLivraison, zone: ZoneLivraison | None) -> int:
    return zone.delai_jours if mode == ModeLivraison.LIVRAISON and zone is not None else 0
