"""Codes de réduction gérés par l'équipe : créer, suivre les utilisations, arrêter. Un code
n'est jamais effacé : les commandes qui l'ont utilisé le gardent."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes.tarifs import aujourd_hui
from boutique.config import ROLE_ADMIN_BOUTIQUE
from boutique.models import CodePromo, Commande, JournalAudit
from boutique.promotions.schemas import CodeVue, ModificationCode, NouveauCode
from boutique.promotions.service import SANS_EFFET, normaliser
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin/codes-promo", tags=["gestion du catalogue"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)


async def _vues(session: AsyncSession, codes: list[CodePromo]) -> list[CodeVue]:
    usages = {
        code: (int(nombre), int(remises or 0))
        for code, nombre, remises in await session.execute(
            select(Commande.code_promo, func.count(), func.sum(Commande.remise))
            .where(Commande.code_promo.in_([c.code for c in codes]))
            .where(Commande.statut.not_in(SANS_EFFET))
            .group_by(Commande.code_promo)
        )
    }
    return [
        CodeVue.model_validate(
            {
                **{k: getattr(c, k) for k in CodeVue.model_fields if hasattr(c, k)},
                "utilisations": usages.get(c.code, (0, 0))[0],
                "remises": usages.get(c.code, (0, 0))[1],
            }
        )
        for c in codes
    ]


@routeur.get("", summary="Codes de réduction et leurs utilisations")
async def lister(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[CodeVue]:
    codes = await session.scalars(select(CodePromo).order_by(CodePromo.cree_le.desc()))
    return await _vues(session, list(codes))


@routeur.post("", status_code=status.HTTP_201_CREATED, summary="Créer un code de réduction")
async def creer(
    donnees: NouveauCode,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CodeVue:
    code = normaliser(donnees.code)
    if await session.scalar(select(CodePromo.id).where(CodePromo.code == code)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Le code {code} existe déjà")
    nouveau = CodePromo(
        **donnees.model_dump(exclude={"code", "debut"}),
        code=code,
        debut=donnees.debut or aujourd_hui(),
    )
    session.add(nouveau)
    await session.flush()
    journaliser(
        session,
        JournalAudit,
        action="code_promo.cree",
        acteur_id=principal.id,
        objet_type="code_promo",
        objet_id=code,
        details={"nature": nouveau.nature, "valeur": nouveau.valeur},
    )
    await session.commit()
    [vue] = await _vues(session, [nouveau])
    return vue


@routeur.patch("/{code_id}", summary="Modifier ou arrêter un code")
async def modifier(
    code_id: UUID,
    donnees: ModificationCode,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CodeVue:
    code = await session.get(CodePromo, code_id)
    if code is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    if changements.get("fin") is not None and changements["fin"] < code.debut:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La fin doit suivre le début")
    for champ, valeur in changements.items():
        if valeur is not None or champ in {"fin", "utilisations_max"}:
            setattr(code, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="code_promo.modifie",
        acteur_id=principal.id,
        objet_type="code_promo",
        objet_id=code.code,
        details={"champs": sorted(changements)},
    )
    await session.commit()
    [vue] = await _vues(session, [code])
    return vue
