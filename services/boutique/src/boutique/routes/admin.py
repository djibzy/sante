"""Administration du catalogue, réservée au rôle boutique:admin."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import CATEGORIE_LIBRE, JournalAudit, PosteAtelier, Produit, Rayon, Variante
from boutique.schemas import (
    CreationProduit,
    CreationRayon,
    CreationVariante,
    ModificationProduit,
    ModificationRayon,
    ProduitDetail,
    RayonPublic,
)
from boutique.vues import vers_detail
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin", tags=["administration"])
administrateur = exiger_role(ROLE_ADMIN_BOUTIQUE)
_PRIX_REQUIS = "Un produit vendu en ligne doit avoir un prix public"


async def _vue_rayon(session: AsyncSession, rayon: Rayon) -> RayonPublic:
    nombre = await session.scalar(
        select(func.count(Produit.id)).where(Produit.rayon_id == rayon.id, Produit.est_actif)
    )
    return RayonPublic(
        id=rayon.id,
        slug=rayon.slug,
        nom=rayon.nom,
        description=rayon.description,
        univers=rayon.univers,
        nombre_produits=nombre or 0,
    )


async def _charger_produit(session: AsyncSession, produit_id: UUID) -> Produit:
    requete = (
        select(Produit)
        .join(Produit.rayon)
        .options(
            contains_eager(Produit.rayon),
            selectinload(Produit.images),
            selectinload(Produit.variantes),
        )
        .where(Produit.id == produit_id)
        .execution_options(populate_existing=True)
    )
    produit = (await session.execute(requete)).scalar_one_or_none()
    if produit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    return produit


def _verifier_promo(prix: int | None, avant_promo: int | None) -> None:
    if avant_promo is not None and (prix is None or avant_promo <= prix):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Le prix barré doit être supérieur au prix de vente",
        )


async def _verifier_poste(session: AsyncSession, code: str | None) -> None:
    if code is not None and not await session.scalar(
        select(PosteAtelier.id).where(PosteAtelier.code == code)
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Poste d'atelier inconnu")


async def _valider(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, message) from exc


@routeur.post("/rayons", status_code=status.HTTP_201_CREATED, summary="Créer un rayon")
async def creer_rayon(
    donnees: CreationRayon,
    principal: Principal = Depends(administrateur),
    session: AsyncSession = Depends(session_db),
) -> RayonPublic:
    rayon = Rayon(**donnees.model_dump())
    session.add(rayon)
    await _valider(session, "Ce slug de rayon est déjà utilisé")
    journaliser(
        session,
        JournalAudit,
        action="rayon.cree",
        acteur_id=principal.id,
        objet_type="rayon",
        objet_id=rayon.id,
    )
    await session.commit()
    return await _vue_rayon(session, rayon)


@routeur.patch("/rayons/{rayon_id}", summary="Modifier un rayon")
async def modifier_rayon(
    rayon_id: UUID,
    donnees: ModificationRayon,
    principal: Principal = Depends(administrateur),
    session: AsyncSession = Depends(session_db),
) -> RayonPublic:
    rayon = await session.get(Rayon, rayon_id)
    if rayon is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rayon introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    for champ, valeur in changements.items():
        setattr(rayon, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="rayon.modifie",
        acteur_id=principal.id,
        objet_type="rayon",
        objet_id=rayon.id,
        details={"champs": sorted(changements)},
    )
    await session.commit()
    return await _vue_rayon(session, rayon)


@routeur.post("/produits", status_code=status.HTTP_201_CREATED, summary="Créer un produit")
async def creer_produit(
    donnees: CreationProduit,
    principal: Principal = Depends(administrateur),
    session: AsyncSession = Depends(session_db),
) -> ProduitDetail:
    rayon = (
        await session.execute(select(Rayon).where(Rayon.slug == donnees.rayon_slug))
    ).scalar_one_or_none()
    if rayon is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Rayon inconnu")
    if donnees.categorie_reglementaire == CATEGORIE_LIBRE and donnees.prix_public is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _PRIX_REQUIS)
    await _verifier_poste(session, donnees.poste_atelier)
    _verifier_promo(donnees.prix_public, donnees.prix_avant_promo)

    produit = Produit(**donnees.model_dump(exclude={"rayon_slug", "variantes"}), rayon_id=rayon.id)
    produit.variantes = [Variante(**v.model_dump()) for v in donnees.variantes]
    session.add(produit)
    await _valider(session, "Ce slug de produit ou une de ces références est déjà utilisé")
    journaliser(
        session,
        JournalAudit,
        action="produit.cree",
        acteur_id=principal.id,
        objet_type="produit",
        objet_id=produit.id,
    )
    await session.commit()
    return vers_detail(await _charger_produit(session, produit.id))


@routeur.patch("/produits/{produit_id}", summary="Modifier un produit")
async def modifier_produit(
    produit_id: UUID,
    donnees: ModificationProduit,
    principal: Principal = Depends(administrateur),
    session: AsyncSession = Depends(session_db),
) -> ProduitDetail:
    produit = await _charger_produit(session, produit_id)
    changements = donnees.model_dump(exclude_unset=True)
    if "poste_atelier" in changements:
        await _verifier_poste(session, changements["poste_atelier"])
    if {"prix_public", "prix_avant_promo"} & changements.keys():
        _verifier_promo(
            changements.get("prix_public", produit.prix_public),
            changements.get("prix_avant_promo", produit.prix_avant_promo),
        )
    for champ, valeur in changements.items():
        setattr(produit, champ, valeur)
    if produit.categorie_reglementaire == CATEGORIE_LIBRE and produit.prix_public is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _PRIX_REQUIS)
    journaliser(
        session,
        JournalAudit,
        action="produit.modifie",
        acteur_id=principal.id,
        objet_type="produit",
        objet_id=produit.id,
        details={"champs": sorted(changements)},
    )
    await session.commit()
    return vers_detail(await _charger_produit(session, produit_id))


@routeur.post(
    "/produits/{produit_id}/variantes",
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une variante (taille, couleur)",
)
async def ajouter_variante(
    produit_id: UUID,
    donnees: CreationVariante,
    principal: Principal = Depends(administrateur),
    session: AsyncSession = Depends(session_db),
) -> ProduitDetail:
    await _charger_produit(session, produit_id)
    variante = Variante(**donnees.model_dump(), produit_id=produit_id)
    session.add(variante)
    await _valider(session, "Cette référence (SKU) est déjà utilisée")
    journaliser(
        session,
        JournalAudit,
        action="variante.ajoutee",
        acteur_id=principal.id,
        objet_type="produit",
        objet_id=produit_id,
        details={"sku": donnees.sku},
    )
    await session.commit()
    return vers_detail(await _charger_produit(session, produit_id))
