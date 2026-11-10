"""Gestion du catalogue par l'équipe : listes complètes (inactifs compris), variantes, photos."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload

from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import ImageProduit, JournalAudit, Produit, Rayon, Variante
from boutique.schemas import (
    ImagePublique,
    ImagesProduit,
    ModificationVariante,
    ProduitGestion,
    RayonGestion,
    VarianteGestion,
)
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin", tags=["gestion du catalogue"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)


def _vue(produit: Produit) -> ProduitGestion:
    return ProduitGestion(
        id=produit.id,
        slug=produit.slug,
        nom=produit.nom,
        resume=produit.resume,
        description=produit.description,
        rayon_slug=produit.rayon.slug,
        rayon_nom=produit.rayon.nom,
        categorie_reglementaire=produit.categorie_reglementaire,
        personnalisable=produit.personnalisable,
        prix_public=produit.prix_public,
        prix_pro=produit.prix_pro,
        delai_jours=produit.delai_jours,
        poste_atelier=produit.poste_atelier,
        seuil_alerte=produit.seuil_alerte,
        est_actif=produit.est_actif,
        variantes=[VarianteGestion.model_validate(v) for v in produit.variantes],
        images=[
            ImagePublique(url=i.url, texte_alternatif=i.texte_alternatif) for i in produit.images
        ],
    )


def _requete() -> Select[Produit]:
    return (
        select(Produit)
        .join(Produit.rayon)
        .options(
            contains_eager(Produit.rayon),
            selectinload(Produit.variantes),
            selectinload(Produit.images),
        )
        .execution_options(populate_existing=True)
    )


async def _produit(session: AsyncSession, produit_id: UUID) -> Produit:
    produit = (
        await session.execute(_requete().where(Produit.id == produit_id))
    ).scalar_one_or_none()
    if produit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produit introuvable")
    return produit


@routeur.get("/rayons", summary="Tous les rayons, actifs ou non")
async def rayons(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[RayonGestion]:
    liste = await session.scalars(select(Rayon).order_by(Rayon.position, Rayon.nom))
    return [RayonGestion.model_validate(r) for r in liste]


@routeur.get("/produits", summary="Tous les produits, actifs ou non")
async def produits(
    q: str | None = Query(None, max_length=100),
    rayon: str | None = Query(None, max_length=80),
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> list[ProduitGestion]:
    requete = _requete().order_by(Rayon.position, Produit.nom)
    if rayon:
        requete = requete.where(Rayon.slug == rayon)
    if q and q.strip():
        motif = f"%{q.strip()}%"
        requete = requete.where(or_(Produit.nom.ilike(motif), Produit.slug.ilike(motif)))
    return [_vue(p) for p in (await session.execute(requete)).scalars().unique()]


@routeur.get("/produits/{produit_id}", summary="Un produit, pour le modifier")
async def produit(
    produit_id: UUID,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> ProduitGestion:
    return _vue(await _produit(session, produit_id))


@routeur.patch("/variantes/{variante_id}", summary="Modifier ou retirer une variante")
async def modifier_variante(
    variante_id: UUID,
    donnees: ModificationVariante,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> ProduitGestion:
    variante = await session.get(Variante, variante_id)
    if variante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    for champ, valeur in changements.items():
        setattr(variante, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="variante.modifiee",
        acteur_id=principal.id,
        objet_type="variante",
        objet_id=variante.id,
        details={"champs": sorted(changements)},
    )
    produit_id = variante.produit_id
    await session.commit()
    return _vue(await _produit(session, produit_id))


@routeur.put("/produits/{produit_id}/images", summary="Photos du produit, dans l'ordre")
async def remplacer_images(
    produit_id: UUID,
    donnees: ImagesProduit,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> ProduitGestion:
    produit = await _produit(session, produit_id)
    produit.images = [
        ImageProduit(url=image.url, texte_alternatif=image.texte_alternatif, position=i)
        for i, image in enumerate(donnees.images)
    ]
    journaliser(
        session,
        JournalAudit,
        action="produit.images",
        acteur_id=principal.id,
        objet_type="produit",
        objet_id=produit.id,
        details={"nombre": len(donnees.images)},
    )
    await session.commit()
    return _vue(await _produit(session, produit_id))
