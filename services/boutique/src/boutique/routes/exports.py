"""Exports pour la comptabilité, au format CSV qu'Excel ouvre tel quel (UTF-8 avec BOM,
point-virgule, dates jj/mm/aaaa, montants entiers en FCFA) : factures, encaissements,
commandes (voir socle.tableurs : cellules neutralisées contre l'injection de formules).
Chaque export est tracé dans le journal d'audit : il contient des données personnelles."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from boutique.commandes.cycle import LIBELLES, Moyen, Statut
from boutique.commandes.pdf import MOYENS
from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import Commande, Facture, JournalAudit, Paiement, Remboursement
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role
from socle.tableurs import en_csv

routeur = APIRouter(prefix="/api/v1/admin/exports", tags=["tableau de bord"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
Nature = Literal["factures", "encaissements", "commandes"]
LIBELLES_MOYENS = {**MOYENS, Moyen.MOBILE_MONEY: "paiement mobile"}
# Devis pas encore acceptés, devis refusés, commandes annulées : le client ne doit rien.
RIEN_A_PAYER = frozenset(
    {Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE, Statut.DEVIS_REFUSE, Statut.ANNULEE}
)


def _bornes(du: date, au: date) -> tuple[datetime, datetime]:
    return datetime.combine(du, time.min, UTC), datetime.combine(
        au + timedelta(days=1), time.min, UTC
    )


async def _factures(session: AsyncSession, debut: datetime, fin: datetime) -> str:
    factures = await session.scalars(
        select(Facture)
        .join(Facture.commande)
        .where(Facture.emise_le >= debut, Facture.emise_le < fin)
        .options(contains_eager(Facture.commande))
        .order_by(Facture.annee, Facture.numero)
    )
    return en_csv(
        ["Facture", "Date", "Commande", "Client", "Structure", "Articles", "Livraison", "Remise",
         "Total", "Payé", "Reste à payer"],
        (
            [f.reference, f.emise_le, f.commande.reference, f.commande.nom_client,
             f.commande.etablissement, f.commande.sous_total, f.commande.frais_livraison,
             f.commande.remise, f.montant, f.commande.montant_paye,
             max(f.commande.total - f.commande.montant_paye, 0)]
            for f in factures
        ),
    )  # fmt: skip


async def _encaissements(session: AsyncSession, debut: datetime, fin: datetime) -> str:
    """Entrées et sorties de caisse : un remboursement au client est une ligne négative."""
    paiements = await session.execute(
        select(Paiement, Commande.numero, Facture)
        .join(Commande, Commande.id == Paiement.commande_id)
        .outerjoin(Facture, Facture.commande_id == Commande.id)
        .where(Paiement.encaisse_le >= debut, Paiement.encaisse_le < fin)
    )
    rendus = await session.execute(
        select(Remboursement, Commande.numero, Facture)
        .join(Commande, Commande.id == Remboursement.commande_id)
        .outerjoin(Facture, Facture.commande_id == Commande.id)
        .where(Remboursement.rembourse_le >= debut, Remboursement.rembourse_le < fin)
    )
    lignes = [
        (p.encaisse_le, "Encaissement", numero, facture, p.moyen, p.montant, p.reference)
        for p, numero, facture in paiements
    ] + [
        (r.rembourse_le, "Remboursement", numero, facture, r.moyen, -r.montant, r.reference)
        for r, numero, facture in rendus
    ]
    return en_csv(
        ["Date", "Opération", "Commande", "Facture", "Moyen", "Montant", "Référence"],
        (
            [le, operation, f"BB-{numero}", facture.reference if facture else None,
             LIBELLES_MOYENS.get(Moyen(moyen), moyen), montant, reference]
            for le, operation, numero, facture, moyen, montant, reference in sorted(
                lignes, key=lambda ligne: ligne[0]
            )
        ),
    )  # fmt: skip


async def _commandes(session: AsyncSession, debut: datetime, fin: datetime) -> str:
    """« Payé » : tout ce que le client a versé ; « Remboursé » : ce qui lui a été rendu."""
    rendu = (
        select(func.coalesce(func.sum(Remboursement.montant), 0))
        .where(Remboursement.commande_id == Commande.id)
        .correlate(Commande)
        .scalar_subquery()
    )
    resultat = await session.execute(
        select(Commande, rendu)
        .where(Commande.cree_le >= debut, Commande.cree_le < fin)
        .order_by(Commande.numero)
    )
    return en_csv(
        ["Commande", "Date", "Statut", "Client", "Structure", "Réception", "Articles", "Livraison",
         "Remise", "Code promo", "Total", "Acompte", "Acompte gardé", "Payé", "Remboursé",
         "Reste à payer"],
        (
            [c.reference, c.cree_le, LIBELLES[Statut(c.statut)], c.nom_client, c.etablissement,
             "livraison" if c.mode_livraison == "livraison" else "retrait", c.sous_total,
             c.frais_livraison, c.remise, c.code_promo, c.total, c.acompte, c.acompte_garde,
             c.montant_paye + rembourse, rembourse,
             0 if Statut(c.statut) in RIEN_A_PAYER else c.reste_a_payer]
            for c, rembourse in resultat
        ),
    )  # fmt: skip


@routeur.get("/{nature}.csv", summary="Export CSV pour la comptabilité")
async def exporter(
    nature: Nature,
    request: Request,
    du: date = Query(description="Premier jour"),
    au: date = Query(description="Dernier jour, compris"),
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> Response:
    if du > au:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Le premier jour doit précéder le dernier"
        )
    if (au - du).days > 366:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Choisissez une période d'un an au plus"
        )
    debut, fin = _bornes(du, au)
    producteurs = {"factures": _factures, "encaissements": _encaissements, "commandes": _commandes}
    contenu = await producteurs[nature](session, debut, fin)
    journaliser(
        session,
        JournalAudit,
        action=f"export.{nature}",
        acteur_id=principal.id,
        objet_type="export",
        objet_id=nature,
        details={"du": str(du), "au": str(au)},
        adresse_ip=request.client.host if request.client else None,
    )
    await session.commit()
    return Response(
        content=contenu.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="bibou-{nature}-{du}-{au}.csv"'},
    )
