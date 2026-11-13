"""Droits des personnes (loi n° 2013-015) : télécharger ses données, supprimer son compte.

La suppression anonymise le compte (le numéro redevient libre) et coupe ses sessions. Chaque
produit oublie de son côté ce qui le concerne : l'interface appelle ensuite la boutique avec le
jeton d'accès, encore valable quelques minutes.
"""

import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from comptes.models import (
    Adhesion,
    CodeVerification,
    Consentement,
    JetonRafraichissement,
    JournalAudit,
    Organisation,
    Utilisateur,
)
from comptes.routes.auth import (
    CHEMIN_COOKIE,
    NOM_COOKIE,
    _hacheur,
    _ip,
    _mot_de_passe_valide,
    _parametres,
)
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, principal_requis

routeur = APIRouter(prefix="/api/v1/auth", tags=["mes données"])
NOM_SUPPRIME = "Compte supprimé"


class Suppression(BaseModel):
    mot_de_passe: str = Field(min_length=1, max_length=128)


async def _compte(session: AsyncSession, principal: Principal) -> Utilisateur:
    utilisateur = await session.get(Utilisateur, principal.id, with_for_update=True)
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
    return utilisateur


@routeur.get("/mes-donnees", summary="Toutes mes données du service Comptes")
async def mes_donnees(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> dict[str, Any]:
    u = await _compte(session, principal)
    consentements = await session.scalars(
        select(Consentement).where(Consentement.utilisateur_id == u.id)
    )
    organisations = await session.execute(
        select(Organisation.nom, Organisation.type, Adhesion.role, Adhesion.cree_le)
        .join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == u.id)
    )
    sessions = await session.scalars(
        select(JetonRafraichissement).where(
            JetonRafraichissement.utilisateur_id == u.id,
            JetonRafraichissement.revoque_le.is_(None),
        )
    )
    journal = await session.scalars(
        select(JournalAudit)
        .where(or_(JournalAudit.acteur_id == u.id, JournalAudit.objet_id == str(u.id)))
        .order_by(JournalAudit.cree_le)
    )
    return {
        "service": "comptes",
        "exporte_le": datetime.now(UTC).isoformat(),
        "compte": {
            "id": str(u.id),
            "nom": u.nom,
            "telephone": u.telephone,
            "langue": u.langue,
            "roles": u.roles,
            "cree_le": u.cree_le.isoformat(),
            "derniere_connexion": u.derniere_connexion.isoformat()
            if u.derniere_connexion
            else None,
        },
        "consentements": [
            {
                "objet": c.objet,
                "version": c.version,
                "accepte_le": c.accepte_le.isoformat(),
                "retire_le": c.retire_le.isoformat() if c.retire_le else None,
            }
            for c in consentements
        ],
        "organisations": [
            {"nom": nom, "type": type_, "role": role, "depuis": depuis.isoformat()}
            for nom, type_, role, depuis in organisations
        ],
        "sessions_ouvertes": [
            {
                "appareil": s.appareil,
                "ouverte_le": s.cree_le.isoformat(),
                "expire_le": s.expire_le.isoformat(),
            }
            for s in sessions
        ],
        "journal": [
            {"action": j.action, "le": j.cree_le.isoformat(), "adresse_ip": j.adresse_ip}
            for j in journal
        ],
    }


@routeur.post(
    "/suppression",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer mon compte (anonymisé, numéro libéré, sessions coupées)",
    dependencies=[Depends(LimiteDebit("suppression", nombre=10, secondes=600))],
)
async def supprimer(
    donnees: Suppression,
    request: Request,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Response:
    u = await _compte(session, principal)
    if not await asyncio.to_thread(_mot_de_passe_valide, u.mot_de_passe_hash, donnees.mot_de_passe):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe incorrect")
    maintenant = datetime.now(UTC)
    u.nom = NOM_SUPPRIME
    u.telephone = f"supprime-{u.id.hex[:11]}"  # le numéro peut servir à un nouveau compte
    u.mot_de_passe_hash = await asyncio.to_thread(_hacheur.hash, secrets.token_urlsafe(32))
    u.roles = []
    u.est_actif = False
    for modele in (Consentement, Adhesion, CodeVerification):
        await session.execute(delete(modele).where(modele.utilisateur_id == u.id))
    await session.execute(
        update(JetonRafraichissement)
        .where(
            JetonRafraichissement.utilisateur_id == u.id,
            JetonRafraichissement.revoque_le.is_(None),
        )
        .values(revoque_le=maintenant)
    )
    journaliser(
        session,
        JournalAudit,
        action="compte.supprime",
        acteur_id=u.id,
        objet_type="utilisateur",
        objet_id=u.id,
        adresse_ip=_ip(request),
    )
    await session.commit()
    reponse = Response(status_code=status.HTTP_204_NO_CONTENT)
    reponse.delete_cookie(
        NOM_COOKIE, path=CHEMIN_COOKIE, domain=_parametres(request).cookie_domaine
    )
    return reponse
