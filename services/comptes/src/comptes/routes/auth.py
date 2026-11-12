"""Inscription, connexion, rafraîchissement, déconnexion et mot de passe (oublié ou changé).

Le jeton d'accès est court (15 minutes) ; le jeton de rafraîchissement, long (30 jours),
change à chaque usage. Réutiliser un jeton déjà remplacé coupe toutes les sessions de la
personne : c'est le signe qu'il a été volé.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from comptes import codes
from comptes.config import LONGUEUR_EQUIPE, ROLES_EQUIPE, ParametresComptes
from comptes.jetons import Signataire, empreinte, nouveau_jeton_rafraichissement
from comptes.models import Consentement, JetonRafraichissement, JournalAudit, Utilisateur
from comptes.schemas import (
    ChangementMotDePasse,
    Connexion,
    DemandeCode,
    DemandeRafraichissement,
    Inscription,
    Jetons,
    Message,
    Reinitialisation,
    UtilisateurPublic,
)
from socle.audit import journaliser
from socle.db import session_db
from socle.limites import LimiteDebit
from socle.security import Principal, principal_requis
from socle.telephones import NumeroInvalide, normaliser_telephone

routeur = APIRouter(prefix="/api/v1/auth", tags=["connexion"])

NOM_COOKIE = "sante_rafraichissement"
CHEMIN_COOKIE = "/api/v1/auth"
_hacheur = PasswordHasher()
_HASH_FACTICE = _hacheur.hash(
    "mot-de-passe-factice"
)  # temps de réponse égal si le compte n'existe pas
_SESSION_EXPIREE = "Session expirée, reconnectez-vous"


def _parametres(request: Request) -> ParametresComptes:
    parametres: ParametresComptes = request.app.state.parametres
    return parametres


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _mot_de_passe_valide(hash_enregistre: str, mot_de_passe: str) -> bool:
    try:
        return _hacheur.verify(hash_enregistre, mot_de_passe)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


async def _emettre_jetons(
    request: Request,
    response: Response,
    session: AsyncSession,
    utilisateur: Utilisateur,
    appareil: str | None = None,
) -> tuple[Jetons, JetonRafraichissement]:
    p = _parametres(request)
    brut, emp = nouveau_jeton_rafraichissement()
    jeton = JetonRafraichissement(
        utilisateur_id=utilisateur.id,
        empreinte=emp,
        appareil=appareil,
        expire_le=datetime.now(UTC) + timedelta(days=p.duree_jeton_rafraichissement_jours),
    )
    session.add(jeton)
    await session.flush()
    response.set_cookie(
        NOM_COOKIE,
        brut,
        max_age=p.duree_jeton_rafraichissement_jours * 86400,
        httponly=True,
        secure=p.cookie_securise,
        samesite="lax",
        domain=p.cookie_domaine,
        path=CHEMIN_COOKIE,
    )
    signataire: Signataire = request.app.state.signataire
    # Un navigateur garde le jeton de rafraîchissement dans le seul cookie httpOnly, hors de
    # portée du JavaScript de la page ; les applications mobiles le reçoivent dans la réponse.
    pour_navigateur = request.headers.get("x-client") == "web"
    jetons = Jetons(
        jeton_acces=signataire.emettre(utilisateur),
        expire_dans=signataire.duree_secondes,
        jeton_rafraichissement=None if pour_navigateur else brut,
        utilisateur=UtilisateurPublic.model_validate(utilisateur),
    )
    return jetons, jeton


@routeur.post(
    "/inscription",
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte",
    dependencies=[Depends(LimiteDebit("inscription", nombre=30, secondes=600))],
)
async def inscription(
    donnees: Inscription,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(session_db),
) -> Jetons:
    p = _parametres(request)
    if not donnees.accepte_conditions:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Il faut accepter les conditions d'utilisation"
        )
    try:
        telephone = normaliser_telephone(donnees.telephone, p.region_telephone)
    except NumeroInvalide as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    mot_de_passe_hash = await asyncio.to_thread(_hacheur.hash, donnees.mot_de_passe)
    utilisateur = Utilisateur(
        telephone=telephone,
        nom=donnees.nom.strip(),
        langue=donnees.langue,
        mot_de_passe_hash=mot_de_passe_hash,
        roles=[],
    )
    session.add(utilisateur)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Un compte existe déjà avec ce numéro"
        ) from exc

    session.add(
        Consentement(
            utilisateur_id=utilisateur.id,
            objet="conditions_utilisation",
            version=p.version_conditions,
        )
    )
    journaliser(
        session,
        JournalAudit,
        action="compte.cree",
        acteur_id=utilisateur.id,
        objet_type="utilisateur",
        objet_id=utilisateur.id,
        adresse_ip=_ip(request),
    )
    jetons, _ = await _emettre_jetons(request, response, session, utilisateur)
    await session.commit()
    return jetons


@routeur.post(
    "/connexion",
    summary="Se connecter avec son numéro et son mot de passe",
    # En plus du verrouillage du compte après 5 échecs : freine les essais en masse.
    dependencies=[Depends(LimiteDebit("connexion", nombre=60, secondes=60))],
)
async def connexion(
    donnees: Connexion,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(session_db),
) -> Jetons:
    p = _parametres(request)
    utilisateur: Utilisateur | None = None
    try:
        telephone = normaliser_telephone(donnees.telephone, p.region_telephone)
        requete = select(Utilisateur).where(Utilisateur.telephone == telephone).with_for_update()
        utilisateur = (await session.execute(requete)).scalar_one_or_none()
    except NumeroInvalide:
        pass

    maintenant = datetime.now(UTC)
    if utilisateur and utilisateur.verrouille_jusqua and utilisateur.verrouille_jusqua > maintenant:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de tentatives. Réessayez dans quelques minutes.",
        )

    hash_enregistre = utilisateur.mot_de_passe_hash if utilisateur else _HASH_FACTICE
    valide = await asyncio.to_thread(_mot_de_passe_valide, hash_enregistre, donnees.mot_de_passe)
    if utilisateur is None or not valide or not utilisateur.est_actif:
        if utilisateur is not None:
            utilisateur.echecs_connexion += 1
            if utilisateur.echecs_connexion >= p.tentatives_max:
                utilisateur.verrouille_jusqua = maintenant + timedelta(
                    minutes=p.verrouillage_minutes
                )
                utilisateur.echecs_connexion = 0
            journaliser(
                session,
                JournalAudit,
                action="connexion.echec",
                objet_type="utilisateur",
                objet_id=utilisateur.id,
                adresse_ip=_ip(request),
            )
            await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Numéro ou mot de passe incorrect")

    utilisateur.echecs_connexion = 0
    utilisateur.verrouille_jusqua = None
    utilisateur.derniere_connexion = maintenant
    if _hacheur.check_needs_rehash(utilisateur.mot_de_passe_hash):
        utilisateur.mot_de_passe_hash = await asyncio.to_thread(_hacheur.hash, donnees.mot_de_passe)
    journaliser(
        session,
        JournalAudit,
        action="connexion.reussie",
        acteur_id=utilisateur.id,
        objet_type="utilisateur",
        objet_id=utilisateur.id,
        adresse_ip=_ip(request),
    )
    jetons, _ = await _emettre_jetons(request, response, session, utilisateur, donnees.appareil)
    await session.commit()
    return jetons


@routeur.post("/rafraichir", summary="Obtenir un nouveau jeton d'accès")
async def rafraichir(
    request: Request,
    response: Response,
    demande: DemandeRafraichissement | None = None,
    jeton_cookie: str | None = Cookie(default=None, alias=NOM_COOKIE),
    session: AsyncSession = Depends(session_db),
) -> Jetons:
    brut = (demande.jeton_rafraichissement if demande else None) or jeton_cookie
    if not brut:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _SESSION_EXPIREE)
    requete = (
        select(JetonRafraichissement)
        .where(JetonRafraichissement.empreinte == empreinte(brut))
        .with_for_update()
    )
    jeton = (await session.execute(requete)).scalar_one_or_none()
    maintenant = datetime.now(UTC)
    if jeton is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _SESSION_EXPIREE)

    if jeton.revoque_le is not None:
        # Jeton déjà utilisé : on coupe toutes les sessions de la personne par précaution.
        await session.execute(
            update(JetonRafraichissement)
            .where(
                JetonRafraichissement.utilisateur_id == jeton.utilisateur_id,
                JetonRafraichissement.revoque_le.is_(None),
            )
            .values(revoque_le=maintenant)
        )
        journaliser(
            session,
            JournalAudit,
            action="session.reutilisation_detectee",
            objet_type="utilisateur",
            objet_id=jeton.utilisateur_id,
            adresse_ip=_ip(request),
        )
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _SESSION_EXPIREE)

    if jeton.expire_le <= maintenant:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _SESSION_EXPIREE)
    utilisateur = await session.get(Utilisateur, jeton.utilisateur_id)
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _SESSION_EXPIREE)

    jetons, nouveau = await _emettre_jetons(request, response, session, utilisateur, jeton.appareil)
    jeton.revoque_le = maintenant
    jeton.remplace_par = nouveau.id
    await session.commit()
    return jetons


@routeur.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT, summary="Fermer la session")
async def deconnexion(
    request: Request,
    demande: DemandeRafraichissement | None = None,
    jeton_cookie: str | None = Cookie(default=None, alias=NOM_COOKIE),
    session: AsyncSession = Depends(session_db),
) -> Response:
    brut = (demande.jeton_rafraichissement if demande else None) or jeton_cookie
    if brut:
        requete = select(JetonRafraichissement).where(
            JetonRafraichissement.empreinte == empreinte(brut)
        )
        jeton = (await session.execute(requete)).scalar_one_or_none()
        if jeton is not None and jeton.revoque_le is None:
            jeton.revoque_le = datetime.now(UTC)
            journaliser(
                session,
                JournalAudit,
                action="session.fermee",
                acteur_id=jeton.utilisateur_id,
                objet_type="utilisateur",
                objet_id=jeton.utilisateur_id,
                adresse_ip=_ip(request),
            )
            await session.commit()
    reponse = Response(status_code=status.HTTP_204_NO_CONTENT)
    reponse.delete_cookie(
        NOM_COOKIE, path=CHEMIN_COOKIE, domain=_parametres(request).cookie_domaine
    )
    return reponse


@routeur.get("/moi", summary="Mon compte")
async def moi(
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> UtilisateurPublic:
    utilisateur = await session.get(Utilisateur, principal.id)
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
    return UtilisateurPublic.model_validate(utilisateur)


CODE_ENVOYE = (
    "Si un compte existe pour ce numéro, un code vient d'être envoyé par SMS. "
    "Il est valable 10 minutes."
)
CODE_INVALIDE = "Code incorrect ou expiré. Demandez un nouveau code si besoin."


def _longueur_suffisante(utilisateur: Utilisateur, mot_de_passe: str) -> None:
    if ROLES_EQUIPE.intersection(utilisateur.roles) and len(mot_de_passe) < LONGUEUR_EQUIPE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Compte de l'équipe : choisissez au moins {LONGUEUR_EQUIPE} caractères.",
        )


async def _nouveau_mot_de_passe(
    session: AsyncSession, utilisateur: Utilisateur, mot_de_passe: str
) -> None:
    """Remplace le mot de passe et coupe toutes les sessions ouvertes (autres appareils)."""
    utilisateur.mot_de_passe_hash = await asyncio.to_thread(_hacheur.hash, mot_de_passe)
    utilisateur.echecs_connexion = 0
    utilisateur.verrouille_jusqua = None
    await session.execute(
        update(JetonRafraichissement)
        .where(
            JetonRafraichissement.utilisateur_id == utilisateur.id,
            JetonRafraichissement.revoque_le.is_(None),
        )
        .values(revoque_le=datetime.now(UTC))
    )


@routeur.post(
    "/mot-de-passe-oublie",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recevoir par SMS un code pour choisir un nouveau mot de passe",
    dependencies=[Depends(LimiteDebit("codes", nombre=10, secondes=600))],
)
async def mot_de_passe_oublie(
    donnees: DemandeCode,
    request: Request,
    taches: BackgroundTasks,
    session: AsyncSession = Depends(session_db),
) -> Message:
    p = _parametres(request)
    try:
        telephone = normaliser_telephone(donnees.telephone, p.region_telephone)
    except NumeroInvalide as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    utilisateur = await session.scalar(
        select(Utilisateur).where(Utilisateur.telephone == telephone).with_for_update()
    )
    # Même réponse, compte ou non : le numéro d'une personne ne se vérifie pas ici.
    if utilisateur is not None and utilisateur.est_actif:
        code = await codes.creer(session, utilisateur, "mot_de_passe", p)
        if code is not None:
            journaliser(
                session,
                JournalAudit,
                action="mot_de_passe.code_envoye",
                objet_type="utilisateur",
                objet_id=utilisateur.id,
                adresse_ip=_ip(request),
            )
            await session.commit()
            texte = (
                f"Yasal Santé : votre code est {code}. Il sert à choisir un nouveau mot de "
                f"passe et expire dans {p.code_validite_minutes} minutes. Ne le donnez à personne."
            )
            taches.add_task(codes.envoyer_sms, request.app, telephone, texte)
    return Message(message=CODE_ENVOYE)


@routeur.post(
    "/reinitialisation",
    summary="Choisir un nouveau mot de passe avec le code reçu par SMS",
    dependencies=[Depends(LimiteDebit("reinitialisation", nombre=30, secondes=600))],
)
async def reinitialiser(
    donnees: Reinitialisation,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(session_db),
) -> Jetons:
    p = _parametres(request)
    utilisateur: Utilisateur | None = None
    try:
        telephone = normaliser_telephone(donnees.telephone, p.region_telephone)
        utilisateur = await session.scalar(
            select(Utilisateur).where(Utilisateur.telephone == telephone).with_for_update()
        )
    except NumeroInvalide:
        pass
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, CODE_INVALIDE)
    _longueur_suffisante(utilisateur, donnees.mot_de_passe)  # avant d'user le code
    if not await codes.verifier(session, utilisateur, "mot_de_passe", donnees.code, p):
        await session.commit()  # l'essai manqué est compté
        raise HTTPException(status.HTTP_400_BAD_REQUEST, CODE_INVALIDE)
    await _nouveau_mot_de_passe(session, utilisateur, donnees.mot_de_passe)
    journaliser(
        session,
        JournalAudit,
        action="mot_de_passe.reinitialise",
        acteur_id=utilisateur.id,
        objet_type="utilisateur",
        objet_id=utilisateur.id,
        adresse_ip=_ip(request),
    )
    jetons, _ = await _emettre_jetons(request, response, session, utilisateur, "navigateur")
    await session.commit()
    return jetons


@routeur.post(
    "/mot-de-passe",
    summary="Changer mon mot de passe",
    dependencies=[Depends(LimiteDebit("changement", nombre=20, secondes=600))],
)
async def changer_mot_de_passe(
    donnees: ChangementMotDePasse,
    request: Request,
    response: Response,
    principal: Principal = Depends(principal_requis),
    session: AsyncSession = Depends(session_db),
) -> Jetons:
    utilisateur = await session.get(Utilisateur, principal.id, with_for_update=True)
    if utilisateur is None or not utilisateur.est_actif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
    valide = await asyncio.to_thread(
        _mot_de_passe_valide, utilisateur.mot_de_passe_hash, donnees.actuel
    )
    if not valide:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    _longueur_suffisante(utilisateur, donnees.nouveau)
    await _nouveau_mot_de_passe(session, utilisateur, donnees.nouveau)
    journaliser(
        session,
        JournalAudit,
        action="mot_de_passe.change",
        acteur_id=utilisateur.id,
        objet_type="utilisateur",
        objet_id=utilisateur.id,
        adresse_ip=_ip(request),
    )
    jetons, _ = await _emettre_jetons(request, response, session, utilisateur, "navigateur")
    await session.commit()
    return jetons
