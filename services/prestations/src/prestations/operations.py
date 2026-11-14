"""Le linge d'une collecte, étape par étape : compté à l'enlèvement, déposé chez le partenaire,
prêt, recompté au retour. Chaque étape est datée, journalisée et, à l'enlèvement comme au
retour, confirmée à la structure par SMS (son bon de collecte).

Les prix sont relevés au moment où ils comptent : le tarif du contrat à l'enlèvement, celui du
partenaire au dépôt. Un tarif changé ensuite ne modifie pas les relevés déjà faits.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prestations import acces, calendrier, notifications
from prestations.config import ParametresPrestations
from prestations.etats import (
    EN_COURS,
    LIBELLES_COLLECTE,
    Formule,
    ModeTarif,
    StatutCollecte,
    StatutContrat,
    passage_autorise,
)
from prestations.linge import Article, libelle
from prestations.models import Collecte, Contrat, JournalAudit, LigneCollecte
from prestations.schemas import Annulation, Depot, Enlevement, LigneComptee, Retour
from socle.audit import journaliser
from socle.security import Principal

_409 = status.HTTP_409_CONFLICT
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
DEJA_ENREGISTREE = "Une collecte est déjà enregistrée pour ce contrat ce jour-là"


def _passer(collecte: Collecte, vers: StatutCollecte) -> None:
    depuis = StatutCollecte(collecte.statut)
    if not passage_autorise(depuis, vers):
        raise HTTPException(
            _409,
            f"Collecte {LIBELLES_COLLECTE[depuis].lower()} : impossible de la passer à "
            f"« {LIBELLES_COLLECTE[vers].lower()} »",
        )
    collecte.statut = vers


def _journaliser(
    session: AsyncSession,
    action: str,
    collecte: Collecte,
    principal: Principal,
    adresse_ip: str | None,
    **details: object,
) -> None:
    journaliser(
        session,
        JournalAudit,
        action=action,
        acteur_id=principal.id,
        objet_type="collecte",
        objet_id=collecte.reference,
        details={"statut": collecte.statut, **details},
        adresse_ip=adresse_ip,
    )


def contrat_actif(contrat: Contrat) -> None:
    if contrat.statut != StatutContrat.ACTIF:
        raise HTTPException(_409, f"Contrat {contrat.reference} suspendu ou terminé")


async def _du_jour(session: AsyncSession, contrat: Contrat, jour: date) -> Collecte | None:
    """La collecte (non annulée) du contrat ce jour-là, verrouillée."""
    return await session.scalar(
        acces.requete_collectes()
        .where(
            Collecte.contrat_id == contrat.id,
            Collecte.prevue_le == jour,
            Collecte.statut != StatutCollecte.ANNULEE,
        )
        .with_for_update(of=Collecte)
    )


async def _enregistrer(session: AsyncSession) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(_409, DEJA_ENREGISTREE) from exc


async def recharger(session: AsyncSession, collecte: Collecte) -> Collecte:
    """La collecte relue avec ses relations, après une écriture (pour la réponse)."""
    relue = await session.scalar(
        acces.requete_collectes()
        .where(Collecte.id == collecte.id)
        .execution_options(populate_existing=True)
    )
    assert relue is not None
    return relue


async def enlever(
    session: AsyncSession,
    parametres: ParametresPrestations,
    principal: Principal,
    donnees: Enlevement,
    adresse_ip: str | None,
) -> Collecte:
    contrat = await acces.contrat_par_id(session, donnees.contrat_id)
    contrat_actif(contrat)
    jour = donnees.jour or calendrier.aujourd_hui()
    collecte = await _du_jour(session, contrat, jour)
    corrigee = collecte is not None and collecte.statut == StatutCollecte.ENLEVEE
    if collecte is None:
        collecte = Collecte(
            contrat_id=contrat.id,
            prevue_le=jour,
            statut=StatutCollecte.ENLEVEE,
            lignes=[],
        )
        session.add(collecte)
    elif corrigee:
        # Recompté avant le dépôt chez le partenaire : le nouveau comptage remplace l'ancien.
        collecte.lignes.clear()
        await session.flush()
    else:
        _passer(collecte, StatutCollecte.ENLEVEE)
    collecte.partenaire_id = collecte.partenaire_id or contrat.partenaire_id
    collecte.enlevee_le = calendrier.maintenant()
    collecte.enlevee_par = principal.id
    collecte.retour_prevu_le = calendrier.date_de_retour(jour, contrat.delai_retour_jours)
    collecte.sacs = donnees.sacs
    collecte.remis_par = donnees.remis_par.strip()
    collecte.observations = donnees.observations.strip()
    a_la_piece = contrat.formule == Formule.PIECE
    collecte.lignes.extend(
        LigneCollecte(
            position=position,
            article=ligne.article,
            precision=ligne.precision,
            quantite_enlevee=ligne.quantite,
            prix_unitaire=contrat.tarifs.get(ligne.article) if a_la_piece else None,
        )
        for position, ligne in enumerate(donnees.lignes)
        if ligne.quantite
    )
    await _enregistrer(session)
    _journaliser(
        session,
        "collecte.enlevee",
        collecte,
        principal,
        adresse_ip,
        contrat=contrat.reference,
        corrigee=corrigee,
        pieces={libelle(Article(ligne.article), ligne.precision): ligne.quantite_enlevee
                for ligne in collecte.lignes},
    )  # fmt: skip
    if contrat.sms_actifs:
        notifications.deposer(
            session,
            "collecte",
            collecte.id,
            contrat.telephone,
            notifications.collecte_enlevee(parametres.nom_service, collecte, corrigee),
        )
    await session.commit()
    return await recharger(session, collecte)


async def deposer(
    session: AsyncSession,
    principal: Principal,
    reference: str,
    donnees: Depot,
    adresse_ip: str | None,
) -> Collecte:
    collecte = await acces.collecte(session, reference, verrou=True)
    _passer(collecte, StatutCollecte.CHEZ_PARTENAIRE)
    identifiant: UUID | None = (
        donnees.partenaire_id or collecte.partenaire_id or collecte.contrat.partenaire_id
    )
    if identifiant is None:
        raise HTTPException(_422, "Choisissez le partenaire qui lave ce linge")
    partenaire = await acces.partenaire(session, identifiant)
    if not partenaire.est_actif:
        raise HTTPException(_422, f"{partenaire.nom} ne reçoit plus de linge")
    poids = (
        Decimal(str(donnees.poids_kg)).quantize(Decimal("0.1"), ROUND_HALF_UP)
        if donnees.poids_kg is not None
        else None
    )
    if partenaire.mode_tarif == ModeTarif.KG and poids is None:
        raise HTTPException(_422, f"Pesée requise : {partenaire.nom} facture au kilo")
    collecte.partenaire_id = partenaire.id
    collecte.poids_kg = poids
    collecte.cout_kg = partenaire.tarif_kg if partenaire.mode_tarif == ModeTarif.KG else None
    for ligne in collecte.lignes:
        ligne.cout_unitaire = (
            partenaire.tarifs.get(ligne.article)
            if partenaire.mode_tarif == ModeTarif.PIECE
            else None
        )
    collecte.deposee_le = calendrier.maintenant()
    _journaliser(
        session,
        "collecte.deposee",
        collecte,
        principal,
        adresse_ip,
        partenaire=partenaire.nom,
        poids_kg=str(poids) if poids is not None else None,
    )
    await session.commit()
    return await recharger(session, collecte)


async def marquer_prete(
    session: AsyncSession, principal: Principal, reference: str, adresse_ip: str | None
) -> Collecte:
    collecte = await acces.collecte(session, reference, verrou=True)
    _passer(collecte, StatutCollecte.PRETE)
    collecte.prete_le = calendrier.maintenant()
    _journaliser(session, "collecte.prete", collecte, principal, adresse_ip)
    await session.commit()
    return await recharger(session, collecte)


def _cle(article: str, precision: str) -> tuple[str, str]:
    return article, precision.lower()


async def rendre(
    session: AsyncSession,
    parametres: ParametresPrestations,
    principal: Principal,
    reference: str,
    donnees: Retour,
    adresse_ip: str | None,
) -> Collecte:
    collecte = await acces.collecte(session, reference, verrou=True)
    _passer(collecte, StatutCollecte.RENDUE)
    comptees: dict[tuple[str, str], LigneComptee] = {
        _cle(ligne.article, ligne.precision): ligne for ligne in donnees.lignes
    }
    attendues = {_cle(ligne.article, ligne.precision): ligne for ligne in collecte.lignes}
    if inconnues := comptees.keys() - attendues.keys():
        article, precision = sorted(inconnues)[0]
        raise HTTPException(
            _422, f"{libelle(Article(article), precision)} : article absent de l'enlèvement"
        )
    if oubliees := attendues.keys() - comptees.keys():
        ligne = attendues[sorted(oubliees)[0]]
        raise HTTPException(
            _422, f"Recomptez chaque article : {libelle(Article(ligne.article), ligne.precision)}"
        )
    for cle, ligne in attendues.items():
        ligne.quantite_rendue = comptees[cle].quantite
    collecte.rendue_le = calendrier.maintenant()
    collecte.rendue_par = principal.id
    collecte.recu_par = donnees.recu_par.strip()
    collecte.observations_retour = donnees.observations.strip()
    manquantes = sum(
        max(0, ligne.quantite_enlevee - (ligne.quantite_rendue or 0)) for ligne in collecte.lignes
    )
    _journaliser(session, "collecte.rendue", collecte, principal, adresse_ip, manquantes=manquantes)
    if collecte.contrat.sms_actifs:
        notifications.deposer(
            session,
            "collecte",
            collecte.id,
            collecte.contrat.telephone,
            notifications.collecte_rendue(parametres.nom_service, collecte),
        )
    # Une pièce manque : la gestion le sait tout de suite, pour la chercher chez le partenaire.
    if manquantes:
        for numero in parametres.telephones_equipe:
            notifications.deposer(
                session,
                "collecte",
                collecte.id,
                numero,
                notifications.manque_pour_l_equipe(collecte),
            )
    await session.commit()
    return await recharger(session, collecte)


async def annuler(
    session: AsyncSession,
    principal: Principal,
    reference: str,
    donnees: Annulation,
    adresse_ip: str | None,
    *,
    gestion: bool,
) -> Collecte:
    collecte = await acces.collecte(session, reference, verrou=True)
    # Linge déjà compté : l'annulation ne sert qu'à corriger une erreur, la gestion décide.
    if collecte.statut == StatutCollecte.ENLEVEE and not gestion:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Linge déjà compté : seule la gestion peut annuler cette collecte",
        )
    _passer(collecte, StatutCollecte.ANNULEE)
    collecte.annulee_le = calendrier.maintenant()
    collecte.motif_annulation = donnees.motif.strip()
    _journaliser(session, "collecte.annulee", collecte, principal, adresse_ip, motif=donnees.motif)
    await session.commit()
    return await recharger(session, collecte)


async def annuler_passage(
    session: AsyncSession,
    principal: Principal,
    contrat_id: UUID,
    jour: date,
    motif: str,
    adresse_ip: str | None,
    *,
    gestion: bool,
) -> Collecte:
    """Rien à collecter ce jour-là (structure fermée, linge pas prêt) : le passage du calendrier
    est noté annulé, avec son motif, et sort de la tournée."""
    contrat = await acces.contrat_par_id(session, contrat_id)
    existante = await _du_jour(session, contrat, jour)
    if existante is not None:
        return await annuler(
            session,
            principal,
            existante.reference,
            Annulation(motif=motif),
            adresse_ip,
            gestion=gestion,
        )
    collecte = Collecte(
        contrat_id=contrat.id,
        prevue_le=jour,
        statut=StatutCollecte.ANNULEE,
        annulee_le=calendrier.maintenant(),
        motif_annulation=motif.strip(),
        lignes=[],
    )
    session.add(collecte)
    await session.flush()
    _journaliser(session, "collecte.annulee", collecte, principal, adresse_ip, motif=motif)
    await session.commit()
    return await recharger(session, collecte)


async def prevoir(
    session: AsyncSession,
    principal: Principal,
    contrat_id: UUID,
    jour: date,
    observations: str,
    adresse_ip: str | None,
) -> Collecte:
    """Collecte ponctuelle, hors du calendrier du contrat : la structure a appelé."""
    contrat = await acces.contrat_par_id(session, contrat_id)
    contrat_actif(contrat)
    if await _du_jour(session, contrat, jour) is not None:
        raise HTTPException(_409, DEJA_ENREGISTREE)
    collecte = Collecte(
        contrat_id=contrat.id,
        partenaire_id=contrat.partenaire_id,
        prevue_le=jour,
        statut=StatutCollecte.PREVUE,
        observations=observations.strip(),
        lignes=[],
    )
    session.add(collecte)
    await _enregistrer(session)
    _journaliser(session, "collecte.prevue", collecte, principal, adresse_ip)
    await session.commit()
    return await recharger(session, collecte)


async def en_cours(session: AsyncSession) -> int:
    """Pièces sorties des structures et pas encore rendues."""
    total = await session.scalar(
        select(func.coalesce(func.sum(LigneCollecte.quantite_enlevee), 0))
        .join(Collecte, Collecte.id == LigneCollecte.collecte_id)
        .where(Collecte.statut.in_(EN_COURS))
    )
    return int(total or 0)
