"""Dépôt d'un avis par le client, relecture par l'équipe, note moyenne des produits.

Un avis par produit et par commande livrée ; il n'est publié qu'après relecture (aucune
information médicale, ni nom complet : seulement le prénom et l'initiale du nom).
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from boutique.avis.schemas import (
    AvisClient,
    AvisCommande,
    AvisGestion,
    AvisPublic,
    Moderation,
    NouvelAvis,
    PageAvis,
    ProduitAEvaluer,
)
from boutique.commandes.cycle import Statut
from boutique.models import CATEGORIE_LIBRE, Avis, Commande, JournalAudit, Produit
from boutique.vues import vue_image
from socle.audit import journaliser
from socle.security import Principal

_409 = status.HTTP_409_CONFLICT
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
PAS_ENCORE = "Vous pourrez donner votre avis une fois la commande reçue."


def auteur_de(nom: str) -> str:
    """« Aminata Traoré » donne « Aminata T. » : jamais de nom complet en ligne."""
    mots = nom.split()
    if not mots:
        return "Client Bibou"
    prenom = mots[0][:40]
    prenom = prenom.capitalize() if prenom.isupper() else prenom
    return prenom + (f" {mots[-1][0].upper()}." if len(mots) > 1 else "")


def _vue_client(avis: Avis | None) -> AvisClient | None:
    if avis is None:
        return None
    return AvisClient.model_validate(avis, from_attributes=True)


async def _produits(session: AsyncSession, commande: Commande) -> list[Produit]:
    """Produits de la commande qui peuvent être notés, dans l'ordre de la commande."""
    ordre: dict[UUID, int] = {}
    for position, ligne in enumerate(commande.lignes):
        if ligne.produit_id is not None:
            ordre.setdefault(ligne.produit_id, position)
    requete = (
        select(Produit)
        .options(selectinload(Produit.images))
        .where(Produit.id.in_(ordre), Produit.categorie_reglementaire == CATEGORIE_LIBRE)
    )
    return sorted(await session.scalars(requete), key=lambda p: ordre[p.id])


async def de_la_commande(session: AsyncSession, commande: Commande) -> AvisCommande:
    produits = await _produits(session, commande)
    deja = {
        a.produit_id: a
        for a in await session.scalars(
            select(Avis)
            .where(Avis.commande_id == commande.id)
            .execution_options(populate_existing=True)
        )
    }
    livree = commande.statut == Statut.LIVREE
    return AvisCommande(
        possible=livree and bool(produits),
        raison=None if livree else PAS_ENCORE,
        produits=[
            ProduitAEvaluer(
                produit_id=p.id,
                slug=p.slug,
                nom=p.nom,
                image=vue_image(p.images[0]) if p.images else None,
                avis=_vue_client(deja.get(p.id)),
            )
            for p in produits
        ],
    )


async def deposer(
    session: AsyncSession,
    commande: Commande,
    donnees: NouvelAvis,
    acteur_id: UUID | None,
    adresse_ip: str | None,
) -> tuple[AvisClient, bool]:
    """Enregistre l'avis (ou le remplace tant qu'il n'est pas publié) ; renvoie (avis, créé)."""
    if commande.statut != Statut.LIVREE:
        raise HTTPException(_409, PAS_ENCORE)
    produit = next(
        (p for p in await _produits(session, commande) if p.id == donnees.produit_id), None
    )
    if produit is None:
        raise HTTPException(_422, "Ce produit ne fait pas partie de votre commande")
    texte = donnees.texte.strip()
    if len(texte) < 10:
        raise HTTPException(_422, "Écrivez quelques mots sur le produit (10 caractères au moins)")
    avis = await session.scalar(
        select(Avis)
        .where(Avis.commande_id == commande.id, Avis.produit_id == produit.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if avis is not None and avis.statut == "publie":
        raise HTTPException(_409, "Votre avis est déjà publié : il ne peut plus être modifié.")
    cree = avis is None
    if avis is None:
        avis = Avis(
            produit_id=produit.id,
            commande_id=commande.id,
            auteur=auteur_de(commande.nom_client),
            statut="en_attente",
            note=donnees.note,
            texte=texte,
        )
        session.add(avis)
    else:  # avis en attente, ou refusé puis réécrit : il repasse en relecture
        avis.note, avis.texte, avis.statut = donnees.note, texte, "en_attente"
        avis.motif_refus = None
    try:
        await session.flush()
    except IntegrityError as exc:  # deux envois simultanés du même avis
        await session.rollback()
        raise HTTPException(_409, "Votre avis est déjà enregistré") from exc
    journaliser(
        session,
        JournalAudit,
        action="avis.depose" if cree else "avis.modifie",
        acteur_id=acteur_id,
        objet_type="produit",
        objet_id=produit.slug,
        details={"commande": commande.reference, "note": donnees.note},
        adresse_ip=adresse_ip,
    )
    vue = _vue_client(avis)
    await session.commit()
    assert vue is not None
    return vue, cree


async def recompter(session: AsyncSession, produit_id: UUID) -> None:
    """Recalcule la note du produit à partir des avis publiés, sous verrou du produit : deux
    décisions simultanées ne peuvent pas se compter l'une sans l'autre."""
    await session.execute(select(Produit.id).where(Produit.id == produit_id).with_for_update())
    nombre, somme = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Avis.note), 0)).where(
                Avis.produit_id == produit_id, Avis.statut == "publie"
            )
        )
    ).one()
    await session.execute(
        update(Produit)
        .where(Produit.id == produit_id)
        .values(nombre_avis=nombre, somme_notes=somme)
    )


async def moderer(
    session: AsyncSession, avis_id: UUID, decision: Moderation, principal: Principal
) -> Avis:
    avis = await session.get(Avis, avis_id, with_for_update=True, populate_existing=True)
    if avis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avis introuvable")
    motif = (decision.motif or "").strip()
    if decision.decision == "refuser" and not motif:
        raise HTTPException(_422, "Indiquez au client pourquoi son avis n'est pas publié")
    avis.statut = "publie" if decision.decision == "publier" else "refuse"
    avis.motif_refus = motif if avis.statut == "refuse" else None
    avis.reponse = (decision.reponse or "").strip() or None
    avis.modere_par, avis.modere_le = principal.id, datetime.now(UTC)
    await session.flush()
    await recompter(session, avis.produit_id)
    journaliser(
        session,
        JournalAudit,
        action=f"avis.{avis.statut}",
        acteur_id=principal.id,
        objet_type="avis",
        objet_id=str(avis.id),
        details={"note": avis.note, "reponse": avis.reponse is not None},
    )
    return avis


async def page_publique(
    session: AsyncSession, produit: Produit, page: int, par_page: int
) -> PageAvis:
    publies = (Avis.produit_id == produit.id, Avis.statut == "publie")
    repartition = {note: 0 for note in range(5, 0, -1)}
    for note, nombre in await session.execute(
        select(Avis.note, func.count()).where(*publies).group_by(Avis.note)
    ):
        repartition[note] = nombre
    total = sum(repartition.values())
    elements = await session.scalars(
        select(Avis)
        .where(*publies)
        .order_by(Avis.cree_le.desc(), Avis.id.desc())
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    return PageAvis(
        moyenne=round(sum(n * c for n, c in repartition.items()) / total, 1) if total else None,
        nombre=total,
        repartition=repartition,
        elements=[
            AvisPublic(
                id=a.id,
                auteur=a.auteur,
                note=a.note,
                texte=a.texte,
                reponse=a.reponse,
                date=a.cree_le,
            )
            for a in elements
        ],
        page=page,
        par_page=par_page,
    )


def vue_gestion(avis: Avis, produit: Produit, numero_commande: int) -> AvisGestion:
    return AvisGestion.model_validate(
        {
            "id": avis.id,
            "produit_id": produit.id,
            "produit_nom": produit.nom,
            "produit_slug": produit.slug,
            "commande_reference": f"BB-{numero_commande}",
            "auteur": avis.auteur,
            "note": avis.note,
            "texte": avis.texte,
            "statut": avis.statut,
            "motif_refus": avis.motif_refus,
            "reponse": avis.reponse,
            "cree_le": avis.cree_le,
            "modere_le": avis.modere_le,
        }
    )
