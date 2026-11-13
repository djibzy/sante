"""Paiement mobile en ligne : ouvrir un paiement, puis créditer la commande quand l'agrégateur
le confirme.

Le statut d'un paiement est toujours relu auprès de l'agrégateur avec notre clé, jamais pris
dans la notification reçue. La relecture se fait sous verrou : un paiement n'est crédité
qu'une fois, même si la notification, le retour du client et le rapprochement arrivent
ensemble.
"""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from boutique.commandes import acces, acompte, operations
from boutique.commandes.cycle import Moyen, Statut
from boutique.config import ParametresBoutique
from boutique.models import Commande, JournalAudit, Paiement, TransactionPaiement
from boutique.notifications import boite, messages
from boutique.paiements.fournisseurs import ErreurFournisseur, Fournisseur, Verification
from boutique.paiements.schemas import DernierPaiement, EtatPaiement
from socle.audit import journaliser

journal = logging.getLogger("boutique.paiements")

MOYENS = ["Orange Money", "Moov Money"]
# Une commande se paie en ligne une fois confirmée par l'équipe (stock, adresse, délai vérifiés
# au téléphone) : aucun remboursement à prévoir pour une commande que l'on ne pourrait pas servir.
# En attente de l'acompte, le client paie l'acompte ou le tout.
PAYABLES = frozenset(
    {
        Statut.ACOMPTE_ATTENDU,
        Statut.CONFIRMEE,
        Statut.EN_PREPARATION,
        Statut.PRETE,
        Statut.EN_LIVRAISON,
        Statut.LIVREE,
    }
)
MULTIPLE = 5  # montants en francs CFA : multiples de 5 chez l'agrégateur
EN_COURS = timedelta(minutes=30)  # au-delà, une tentative sans réponse n'est plus affichée
RAPPROCHEMENT = (timedelta(minutes=2), timedelta(hours=24))  # âge des tentatives relues
TENTATIVES_PAR_HEURE = 10


@dataclass(frozen=True)
class Examen:
    possible: bool
    raison: str | None = None  # à afficher au client quand ce n'est pas possible


def examiner(commande: Commande) -> Examen:
    statut = Statut(commande.statut)
    if statut == Statut.EN_ATTENTE:
        return Examen(
            False,
            "Le paiement en ligne s'ouvre dès que nous avons confirmé votre commande par "
            "téléphone. Vous pouvez aussi payer à la livraison.",
        )
    if statut in {Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE}:
        return Examen(False, "Le paiement en ligne s'ouvre quand le devis est accepté.")
    if statut not in PAYABLES:
        return Examen(False)  # annulée, devis refusé : rien à proposer
    if commande.reste_a_payer == 0:
        return Examen(False, "Cette commande est entièrement payée. Merci !")
    if not montants(commande):
        return Examen(False, "Ce montant ne se paie pas en ligne : réglez-le à la livraison.")
    return Examen(True)


def montants(commande: Commande) -> dict[str, int]:
    """Ce qui se paie en ligne : l'acompte quand il est attendu, et le solde (le reste à payer),
    s'ils sont des multiples de 5 FCFA."""
    choix: dict[str, int] = {}
    du = acompte.restant(commande)
    attendu = commande.statut == Statut.ACOMPTE_ATTENDU
    if attendu and 0 < du < commande.reste_a_payer and du % MULTIPLE == 0:
        choix["acompte"] = du
    if commande.reste_a_payer and commande.reste_a_payer % MULTIPLE == 0:
        choix["solde"] = commande.reste_a_payer
    return choix


def moyen_de(operateur: str | None) -> Moyen:
    """Code opérateur de l'agrégateur (OM, OMML, MOOVML, FLOOZ…) vers notre moyen de paiement."""
    code = (operateur or "").upper()
    if code.startswith("OM"):
        return Moyen.ORANGE_MONEY
    if "MOOV" in code or "FLOOZ" in code:
        return Moyen.MOOV_MONEY
    return Moyen.MOBILE_MONEY


def _fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def _vue(transaction: TransactionPaiement | None, maintenant: datetime) -> DernierPaiement | None:
    if transaction is None:
        return None
    if transaction.statut == "initiee":
        if maintenant - transaction.cree_le > EN_COURS:
            return None  # abandonnée sur la page de paiement
        vue = "en_cours"
    elif transaction.statut == "anomalie":
        vue = "a_verifier"
    else:
        vue = transaction.statut
    return DernierPaiement.model_validate(
        {"statut": vue, "montant": transaction.montant, "cree_le": transaction.cree_le}
    )


async def etat(
    session: AsyncSession, commande: Commande, ouvert: bool, maintenant: datetime | None = None
) -> EtatPaiement:
    examen = examiner(commande)
    derniere = await session.scalar(
        select(TransactionPaiement)
        .where(TransactionPaiement.commande_id == commande.id)
        .order_by(TransactionPaiement.cree_le.desc(), TransactionPaiement.id.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )
    return EtatPaiement(
        disponible=ouvert,
        possible=ouvert and examen.possible,
        montant=commande.reste_a_payer,
        acompte=montants(commande).get("acompte") if examen.possible else None,
        raison=examen.raison if ouvert else None,
        moyens=MOYENS if ouvert else [],
        dernier=_vue(derniere, maintenant or datetime.now(UTC)),
    )


async def ouvrir(
    session: AsyncSession,
    parametres: ParametresBoutique,
    fournisseur: Fournisseur,
    commande: Commande,
    acteur_id: UUID | None,
    adresse_ip: str | None,
    objet: str = "solde",
) -> str:
    """Enregistre la tentative (acompte ou solde) et renvoie l'adresse de la page de paiement de
    l'agrégateur."""
    examen = examiner(commande)
    if not examen.possible:
        raise HTTPException(
            status.HTTP_409_CONFLICT, examen.raison or "Cette commande ne se paie pas en ligne"
        )
    choix = montants(commande)
    if objet not in choix:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce montant ne se paie pas en ligne")
    depuis = datetime.now(UTC) - timedelta(hours=1)
    recentes = await session.scalar(
        select(func.count())
        .select_from(TransactionPaiement)
        .where(
            TransactionPaiement.commande_id == commande.id, TransactionPaiement.cree_le >= depuis
        )
    )
    if (recentes or 0) >= TENTATIVES_PAR_HEURE:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Trop de tentatives de paiement : réessayez dans une heure, ou payez à la livraison.",
        )
    transaction = TransactionPaiement(
        commande_id=commande.id,
        fournisseur=fournisseur.nom,
        transaction_id=f"BB{commande.numero}T{secrets.token_hex(8)}",
        montant=choix[objet],
        statut="initiee",
    )
    session.add(transaction)
    await session.flush()
    base = parametres.url_publique.rstrip("/")
    try:
        adresse = await fournisseur.initier(
            transaction_id=transaction.transaction_id,
            montant=transaction.montant,
            description=("Acompte commande" if objet == "acompte" else "Commande")
            + f" {commande.reference} Bibou",
            reference=commande.reference,
            url_retour=f"{base}/api/v1/paiements/retour/{commande.reference}",
            url_notification=f"{base}/api/v1/paiements/{fournisseur.nom}/notification",
        )
    except ErreurFournisseur as exc:
        await session.rollback()
        journal.warning("Ouverture du paiement refusée", extra={"erreur": str(exc)[:200]})
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Le paiement mobile ne répond pas. Réessayez dans un instant, ou payez à la livraison.",
        ) from exc
    transaction.adresse_paiement = adresse[:500]
    journaliser(
        session,
        JournalAudit,
        action="paiement.ouvert",
        acteur_id=acteur_id,
        objet_type="commande",
        objet_id=commande.reference,
        details={
            "montant": transaction.montant,
            "objet": objet,
            "transaction": transaction.transaction_id,
        },
        adresse_ip=adresse_ip,
    )
    await session.commit()
    return adresse


async def verifier(
    session: AsyncSession, fournisseur: Fournisseur, transaction_id: str, *, attendre: bool = True
) -> TransactionPaiement | None:
    """Relit une tentative auprès de l'agrégateur et l'applique. Sans `attendre`, une tentative
    déjà relue au même moment par un autre appel est laissée à celui-ci. L'appelant valide."""
    requete = (
        select(TransactionPaiement)
        .where(TransactionPaiement.transaction_id == transaction_id)
        .with_for_update(skip_locked=not attendre)
        .execution_options(populate_existing=True)
    )
    transaction = await session.scalar(requete)
    if transaction is None or transaction.statut != "initiee":
        return transaction  # inconnue, ou déjà traitée : rien à refaire
    if transaction.fournisseur != fournisseur.nom:
        return transaction
    try:
        verification = await fournisseur.verifier(transaction)
    except ErreurFournisseur as exc:
        journal.warning(
            "Vérification du paiement impossible",
            extra={"transaction": transaction.transaction_id, "erreur": str(exc)[:200]},
        )
        return transaction
    await appliquer(session, transaction, verification)
    return transaction


async def appliquer(
    session: AsyncSession, transaction: TransactionPaiement, verification: Verification
) -> None:
    if verification.statut == "en_attente":
        return  # le client n'a pas encore validé sur son téléphone
    if verification.statut == "refusee":
        transaction.statut = "refusee"
        return
    transaction.operateur = (verification.operateur or "")[:20] or None
    transaction.reference_operateur = (verification.reference_operateur or "")[:80] or None
    await acces.verrouiller(session, transaction.commande_id)
    commande = await acces.charger_par_id(session, transaction.commande_id)
    statut = Statut(commande.statut)

    if verification.montant != transaction.montant or (verification.devise or "XOF") != "XOF":
        transaction.statut = "anomalie"
        recu = f"{verification.montant} {verification.devise or ''}".strip()
        operations.evenement(
            commande,
            statut,
            None,
            f"Paiement en ligne {transaction.transaction_id} à vérifier : {recu} reçus pour "
            f"{_fcfa(transaction.montant)} attendus. Rien n'a été crédité.",
            visible_client=False,
        )
        journaliser(
            session,
            JournalAudit,
            action="paiement.anomalie",
            acteur_id=None,
            objet_type="commande",
            objet_id=commande.reference,
            details={
                "transaction": transaction.transaction_id,
                "attendu": transaction.montant,
                "recu": verification.montant,
                "devise": verification.devise,
            },
        )
        journal.error("Paiement en ligne à vérifier", extra={"commande": commande.reference})
        return

    paiement = Paiement(
        montant=transaction.montant,
        moyen=moyen_de(verification.operateur),
        reference=transaction.reference_operateur or transaction.transaction_id,
        encaisse_par=None,  # payé en ligne par le client
    )
    commande.paiements.append(paiement)
    commande.montant_paye += transaction.montant
    await session.flush()
    transaction.statut = "acceptee"
    transaction.paiement_id = paiement.id
    journaliser(
        session,
        JournalAudit,
        action="paiement.en_ligne",
        acteur_id=None,
        objet_type="commande",
        objet_id=commande.reference,
        details={
            "montant": transaction.montant,
            "moyen": paiement.moyen,
            "transaction": transaction.transaction_id,
        },
    )
    # L'argent est reçu : on l'enregistre toujours, et l'équipe voit ce qu'il faut rendre.
    note = None
    if statut in {Statut.ANNULEE, Statut.DEVIS_REFUSE}:
        note = f"Paiement en ligne de {_fcfa(transaction.montant)} reçu après l'annulation"
    elif commande.montant_paye > commande.total:
        note = f"Trop-perçu de {_fcfa(commande.montant_paye - commande.total)} (paiement en ligne)"
    if note:
        note = f"{note} : à rembourser."
        operations.evenement(commande, statut, None, note, visible_client=False)
    # Acompte couvert : la fabrication démarre, et le SMS de confirmation dit l'acompte reçu.
    if not await operations.apres_paiement(session, commande, None):
        boite.deposer(session, commande, messages.paiement_recu(commande, transaction.montant))


async def verifier_commande(
    session: AsyncSession, fournisseur: Fournisseur, commande: Commande
) -> None:
    """Retour du client sur le site : relit ses tentatives en attente."""
    depuis = datetime.now(UTC) - RAPPROCHEMENT[1]
    identifiants = list(
        await session.scalars(
            select(TransactionPaiement.transaction_id).where(
                TransactionPaiement.commande_id == commande.id,
                TransactionPaiement.statut == "initiee",
                TransactionPaiement.cree_le >= depuis,
            )
        )
    )
    for identifiant in identifiants:
        await verifier(session, fournisseur, identifiant, attendre=False)
    await session.commit()


async def rapprocher(
    sessions: async_sessionmaker[AsyncSession],
    fournisseur: Fournisseur,
    maintenant: datetime | None = None,
) -> int:
    """Relit les tentatives restées en attente : notification perdue, client parti avant de
    revenir sur le site. Renvoie le nombre de tentatives relues."""
    maintenant = maintenant or datetime.now(UTC)
    async with sessions() as session:
        identifiants = list(
            await session.scalars(
                select(TransactionPaiement.transaction_id)
                .where(
                    TransactionPaiement.statut == "initiee",
                    TransactionPaiement.fournisseur == fournisseur.nom,
                    TransactionPaiement.cree_le <= maintenant - RAPPROCHEMENT[0],
                    TransactionPaiement.cree_le >= maintenant - RAPPROCHEMENT[1],
                )
                .order_by(TransactionPaiement.cree_le)
                .limit(50)
            )
        )
        await session.commit()
        for identifiant in identifiants:
            await verifier(session, fournisseur, identifiant, attendre=False)
            await session.commit()  # une tentative par transaction : verrous courts
    return len(identifiants)
