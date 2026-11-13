"""Exports pour la comptabilité, au format CSV qu'Excel ouvre tel quel (UTF-8 avec BOM,
point-virgule, dates jj/mm/aaaa, montants entiers en FCFA) : factures, encaissements,
commandes. Une cellule qui commencerait par = + - @ est neutralisée (injection de formules).
Chaque export est tracé dans le journal d'audit : il contient des données personnelles."""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from boutique.commandes.cycle import LIBELLES, Moyen, Statut
from boutique.commandes.pdf import MOYENS
from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import Commande, Facture, JournalAudit, Paiement
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin/exports", tags=["tableau de bord"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
Nature = Literal["factures", "encaissements", "commandes"]
DANGEREUX = ("=", "+", "-", "@", "\t", "\r")
LIBELLES_MOYENS = {**MOYENS, Moyen.MOBILE_MONEY: "paiement mobile"}


def cellule(valeur: object) -> str | int:
    if valeur is None:
        return ""
    if isinstance(valeur, int):
        return valeur
    if isinstance(valeur, datetime):
        return f"{valeur:%d/%m/%Y}"
    if isinstance(valeur, date):
        return f"{valeur:%d/%m/%Y}"
    texte = str(valeur)
    return f"'{texte}" if texte.startswith(DANGEREUX) else texte


def en_csv(entetes: Sequence[str], lignes: Iterable[Sequence[object]]) -> str:
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
    ecrivain.writerow(entetes)
    for ligne in lignes:
        ecrivain.writerow([cellule(v) for v in ligne])
    return "﻿" + tampon.getvalue()


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
    resultat = await session.execute(
        select(Paiement, Commande.numero, Facture)
        .join(Commande, Commande.id == Paiement.commande_id)
        .outerjoin(Facture, Facture.commande_id == Commande.id)
        .where(Paiement.encaisse_le >= debut, Paiement.encaisse_le < fin)
        .order_by(Paiement.encaisse_le)
    )
    return en_csv(
        ["Date", "Commande", "Facture", "Moyen", "Montant", "Référence"],
        (
            [p.encaisse_le, f"BB-{numero}", facture.reference if facture else None,
             LIBELLES_MOYENS.get(Moyen(p.moyen), p.moyen), p.montant, p.reference]
            for p, numero, facture in resultat
        ),
    )  # fmt: skip


async def _commandes(session: AsyncSession, debut: datetime, fin: datetime) -> str:
    commandes = await session.scalars(
        select(Commande)
        .where(Commande.cree_le >= debut, Commande.cree_le < fin)
        .order_by(Commande.numero)
    )
    return en_csv(
        ["Commande", "Date", "Statut", "Client", "Structure", "Réception", "Articles", "Livraison",
         "Remise", "Code promo", "Total", "Acompte", "Acompte gardé", "Payé", "Reste à payer"],
        (
            [c.reference, c.cree_le, LIBELLES[Statut(c.statut)], c.nom_client, c.etablissement,
             "livraison" if c.mode_livraison == "livraison" else "retrait", c.sous_total,
             c.frais_livraison, c.remise, c.code_promo, c.total, c.acompte, c.acompte_garde,
             c.montant_paye, max(c.total - c.montant_paye, 0)]
            for c in commandes
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
