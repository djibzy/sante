"""Droits des personnes, côté boutique : télécharger ses commandes et ses avis, et faire
oublier son compte quand on le supprime (le service Comptes anonymise le compte lui-même).

Seules les commandes passées avec le compte sont concernées : une commande passée sans
compte se retrouve avec son lien de suivi.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.avis.service import recompter
from boutique.commandes import acces
from boutique.commandes.cycle import Statut
from boutique.commandes.vues import vue_client
from boutique.entretien import anonymiser
from boutique.models import Avis, Commande, Facture, JournalAudit, Produit
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, principal_requis

routeur = APIRouter(prefix="/api/v1/mes-donnees", tags=["mes données"])
# Une commande encore attendue garde le nom et le téléphone de la personne : on la livre.
EN_COURS = frozenset(
    {
        Statut.EN_ATTENTE,
        Statut.ACOMPTE_ATTENDU,
        Statut.DEVIS_DEMANDE,
        Statut.DEVIS_ENVOYE,
        Statut.CONFIRMEE,
        Statut.EN_PREPARATION,
        Statut.PRETE,
        Statut.EN_LIVRAISON,
    }
)


class Oubli(BaseModel):
    possible: bool
    en_cours: list[str]


class BilanOubli(BaseModel):
    commandes_anonymisees: int
    commandes_detachees: int  # facturées : gardées 10 ans pour les comptes, sans lien au compte
    avis_effaces: int


async def _commandes(session: AsyncSession, client_id: object) -> list[tuple[Any, int, str, bool]]:
    facturee = exists().where(Facture.commande_id == Commande.id)
    requete = select(Commande.id, Commande.numero, Commande.statut, facturee).where(
        Commande.client_id == client_id
    )
    return [(i, n, s, bool(f)) for i, n, s, f in await session.execute(requete)]


@routeur.get("", summary="Mes commandes et mes avis, pour les télécharger")
async def mes_donnees(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> dict[str, Any]:
    commandes = await acces.charger_du_client(session, principal.id)
    avis = await session.execute(
        select(Avis, Produit.nom)
        .join(Produit, Produit.id == Avis.produit_id)
        .where(Avis.commande_id.in_([c.id for c in commandes]))
    )
    return {
        "service": "boutique",
        "exporte_le": datetime.now(UTC).isoformat(),
        "commandes": [vue_client(c).model_dump(mode="json") for c in commandes],
        "avis": [
            {
                "produit": nom,
                "note": a.note,
                "texte": a.texte,
                "statut": a.statut,
                "ecrit_le": a.cree_le.isoformat(),
            }
            for a, nom in avis
        ],
    }


@routeur.get("/oubli", summary="Mon compte peut-il être oublié de la boutique ?")
async def oubli_possible(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Oubli:
    en_cours = [
        f"BB-{n}" for _, n, s, _ in await _commandes(session, principal.id) if s in EN_COURS
    ]
    return Oubli(possible=not en_cours, en_cours=en_cours)


@routeur.post(
    "/oubli",
    summary="Oublier mon compte : commandes anonymisées ou détachées, avis effacés",
    dependencies=[Depends(LimiteDebit("oubli", nombre=10, secondes=600))],
)
async def oublier(
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> BilanOubli:
    commandes = await _commandes(session, principal.id)
    en_cours = [f"BB-{n}" for _, n, s, _ in commandes if s in EN_COURS]
    if en_cours:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Commande en cours : {', '.join(en_cours)}. Attendez sa remise, ou annulez-la, "
            "avant de supprimer votre compte.",
        )
    toutes = [i for i, _, _, _ in commandes]
    facturees = [i for i, _, _, f in commandes if f]
    produits = set(
        await session.scalars(select(Avis.produit_id).where(Avis.commande_id.in_(toutes)))
    )
    effaces = await session.execute(delete(Avis).where(Avis.commande_id.in_(toutes)))
    for produit_id in produits:
        await recompter(session, produit_id)
    await anonymiser(session, [i for i in toutes if i not in facturees])
    if facturees:
        await session.execute(
            update(Commande).where(Commande.id.in_(facturees)).values(client_id=None)
        )
    bilan = BilanOubli(
        commandes_anonymisees=len(toutes) - len(facturees),
        commandes_detachees=len(facturees),
        avis_effaces=getattr(effaces, "rowcount", 0) or 0,
    )
    journaliser(
        session,
        JournalAudit,
        action="compte.oubli",
        acteur_id=principal.id,
        objet_type="client",
        objet_id=str(principal.id),
        details=bilan.model_dump(),
        adresse_ip=request.client.host if request.client else None,
    )
    await session.commit()
    return bilan
