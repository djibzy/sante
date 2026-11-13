"""Calcul des indicateurs sur une période, à partir des commandes et de leurs étapes datées :
rien n'est saisi deux fois. Les dates sont celles de Bamako (temps universel, sans heure d'été).
"""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Date, Float, case, cast, desc, distinct, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Subquery
from sqlalchemy.sql.expression import Exists

from boutique.atelier.stock import lignes_de_stock
from boutique.commandes.cycle import EN_ATTENTE_DE_L_EQUIPE, Statut
from boutique.indicateurs.schemas import (
    Alertes,
    Clients,
    Delais,
    Devis,
    Point,
    TableauDeBord,
    VenteProduit,
    Ventes,
)
from boutique.models import (
    Avis,
    Commande,
    EvenementCommande,
    LigneCommande,
    Notification,
    Paiement,
    Produit,
    TransactionPaiement,
)

EN_COURS = (Statut.CONFIRMEE, Statut.EN_PREPARATION, Statut.PRETE, Statut.EN_LIVRAISON)
JOURS_PAR_POINT_MAX = 31  # au-delà, la série est donnée par semaine


def _bornes(du: date, au: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(du, time.min, tzinfo=UTC),
        datetime.combine(au + timedelta(days=1), time.min, tzinfo=UTC),
    )


def _etape(*statuts: Statut) -> Subquery:
    """Première date à laquelle chaque commande est passée par l'un de ces statuts."""
    return (
        select(
            EvenementCommande.commande_id.label("commande_id"),
            func.min(EvenementCommande.cree_le).label("le"),
        )
        .where(EvenementCommande.statut.in_(statuts))
        .group_by(EvenementCommande.commande_id)
        .subquery()
    )


# Confirmée par l'équipe : directement, ou d'abord « en attente de l'acompte ».
CONFIRMATION = (Statut.CONFIRMEE, Statut.ACOMPTE_ATTENDU)


def _issue_d_un_devis() -> Exists:
    """La commande a commencé par une demande de devis."""
    return (
        exists()
        .where(EvenementCommande.commande_id == Commande.id)
        .where(EvenementCommande.statut == Statut.DEVIS_DEMANDE)
    )


async def _compter_etape(
    session: AsyncSession, statut: Statut, debut: datetime, fin: datetime
) -> int:
    nombre = await session.scalar(
        select(func.count(distinct(EvenementCommande.commande_id))).where(
            EvenementCommande.statut == statut,
            EvenementCommande.cree_le >= debut,
            EvenementCommande.cree_le < fin,
        )
    )
    return int(nombre or 0)


async def _ventes(session: AsyncSession, debut: datetime, fin: datetime) -> Ventes:
    livree = _etape(Statut.LIVREE)
    nombre, chiffre = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Commande.total), 0))
            .select_from(Commande)
            .join(livree, livree.c.commande_id == Commande.id)
            .where(livree.c.le >= debut, livree.c.le < fin)
        )
    ).one()
    recues = await session.scalar(
        select(func.count())
        .select_from(Commande)
        .where(Commande.cree_le >= debut, Commande.cree_le < fin, ~_issue_d_un_devis())
    )
    par_moyen: dict[str, int] = {}
    en_ligne = 0
    for moyen, sans_equipe, montant in await session.execute(
        select(Paiement.moyen, Paiement.encaisse_par.is_(None), func.sum(Paiement.montant))
        .where(Paiement.encaisse_le >= debut, Paiement.encaisse_le < fin)
        .group_by(Paiement.moyen, Paiement.encaisse_par.is_(None))
    ):
        par_moyen[moyen] = par_moyen.get(moyen, 0) + int(montant)
        en_ligne += int(montant) if sans_equipe else 0
    a_encaisser = await session.scalar(
        select(func.coalesce(func.sum(Commande.total - Commande.montant_paye), 0)).where(
            Commande.statut == Statut.LIVREE, Commande.total > Commande.montant_paye
        )
    )
    return Ventes(
        commandes_recues=int(recues or 0),
        commandes_livrees=int(nombre),
        chiffre_affaires=int(chiffre),
        panier_moyen=round(int(chiffre) / int(nombre)) if nombre else None,
        encaisse=sum(par_moyen.values()),
        encaisse_par_moyen=par_moyen,
        encaisse_en_ligne=en_ligne,
        a_encaisser=int(a_encaisser or 0),
        annulees=await _compter_etape(session, Statut.ANNULEE, debut, fin),
    )


async def _devis(session: AsyncSession, debut: datetime, fin: datetime) -> Devis:
    confirmee = _etape(*CONFIRMATION)
    acceptes = await session.scalar(
        select(func.count())
        .select_from(Commande)
        .join(confirmee, confirmee.c.commande_id == Commande.id)
        .where(confirmee.c.le >= debut, confirmee.c.le < fin, _issue_d_un_devis())
    )
    acceptes = int(acceptes or 0)
    refuses = await _compter_etape(session, Statut.DEVIS_REFUSE, debut, fin)
    return Devis(
        demandes=await _compter_etape(session, Statut.DEVIS_DEMANDE, debut, fin),
        envoyes=await _compter_etape(session, Statut.DEVIS_ENVOYE, debut, fin),
        acceptes=acceptes,
        refuses=refuses,
        taux_acceptation=round(acceptes / (acceptes + refuses), 3) if acceptes + refuses else None,
    )


async def _delais(session: AsyncSession, debut: datetime, fin: datetime) -> Delais:
    confirmee, livree = _etape(*CONFIRMATION), _etape(Statut.LIVREE)
    secondes = func.extract("epoch", confirmee.c.le - Commande.cree_le)
    confirmation = await session.scalar(
        select(func.avg(secondes))
        .select_from(Commande)
        .join(confirmee, confirmee.c.commande_id == Commande.id)
        .where(confirmee.c.le >= debut, confirmee.c.le < fin, ~_issue_d_un_devis())
    )
    livraison = await session.scalar(
        select(func.avg(func.extract("epoch", livree.c.le - Commande.cree_le)))
        .select_from(Commande)
        .join(livree, livree.c.commande_id == Commande.id)
        .where(livree.c.le >= debut, livree.c.le < fin, ~_issue_d_un_devis())
    )
    a_l_heure = await session.scalar(
        select(
            func.avg(
                cast(case((cast(livree.c.le, Date) <= Commande.date_promise, 1), else_=0), Float)
            )
        )
        .select_from(Commande)
        .join(livree, livree.c.commande_id == Commande.id)
        .where(livree.c.le >= debut, livree.c.le < fin, Commande.date_promise.is_not(None))
    )
    return Delais(
        confirmation_heures=round(float(confirmation) / 3600, 1)
        if confirmation is not None
        else None,
        livraison_jours=round(float(livraison) / 86400, 1) if livraison is not None else None,
        a_l_heure=round(float(a_l_heure), 3) if a_l_heure is not None else None,
    )


async def _clients(session: AsyncSession, debut: datetime, fin: datetime) -> Clients:
    clients = await session.scalar(
        select(func.count(distinct(Commande.telephone))).where(
            Commande.cree_le >= debut, Commande.cree_le < fin
        )
    )
    premiere = (
        select(Commande.telephone, func.min(Commande.cree_le).label("le"))
        .group_by(Commande.telephone)
        .subquery()
    )
    nouveaux = await session.scalar(
        select(func.count())
        .select_from(premiere)
        .where(premiere.c.le >= debut, premiere.c.le < fin)
    )
    publies = await session.scalar(
        select(func.count())
        .select_from(Avis)
        .where(Avis.statut == "publie", Avis.modere_le >= debut, Avis.modere_le < fin)
    )
    nombre, somme = (
        await session.execute(
            select(
                func.coalesce(func.sum(Produit.nombre_avis), 0),
                func.coalesce(func.sum(Produit.somme_notes), 0),
            )
        )
    ).one()
    a_relire = await session.scalar(
        select(func.count()).select_from(Avis).where(Avis.statut == "en_attente")
    )
    return Clients(
        clients=int(clients or 0),
        nouveaux=int(nouveaux or 0),
        avis_publies=int(publies or 0),
        note_moyenne=round(int(somme) / int(nombre), 1) if nombre else None,
        avis_a_relire=int(a_relire or 0),
    )


async def _meilleures_ventes(
    session: AsyncSession, debut: datetime, fin: datetime, nombre: int = 5
) -> list[VenteProduit]:
    livree = _etape(Statut.LIVREE)
    quantite = func.sum(LigneCommande.quantite)
    requete = (
        select(Produit.slug, Produit.nom, quantite, func.sum(LigneCommande.montant))
        .select_from(LigneCommande)
        .join(livree, livree.c.commande_id == LigneCommande.commande_id)
        .join(Produit, Produit.id == LigneCommande.produit_id)
        .where(livree.c.le >= debut, livree.c.le < fin)
        .group_by(Produit.id, Produit.slug, Produit.nom)
        .order_by(desc(quantite), Produit.nom)
        .limit(nombre)
    )
    return [
        VenteProduit(produit_slug=slug, libelle=nom, quantite=int(q), montant=int(m))
        for slug, nom, q, m in await session.execute(requete)
    ]


async def _alertes(session: AsyncSession, aujourd_hui: date) -> Alertes:
    a_traiter = await session.scalar(
        select(func.count())
        .select_from(Commande)
        .where(Commande.statut.in_(EN_ATTENTE_DE_L_EQUIPE))
    )
    en_retard = await session.scalar(
        select(func.count())
        .select_from(Commande)
        .where(Commande.statut.in_(EN_COURS), Commande.date_promise < aujourd_hui)
    )
    echecs = await session.scalar(
        select(func.count()).select_from(Notification).where(Notification.etat == "echec")
    )
    a_verifier = await session.scalar(
        select(func.count())
        .select_from(TransactionPaiement)
        .where(TransactionPaiement.statut == "anomalie")
    )
    acomptes = await session.scalar(
        select(func.count()).select_from(Commande).where(Commande.statut == Statut.ACOMPTE_ATTENDU)
    )
    return Alertes(
        a_traiter=int(a_traiter or 0),
        acomptes_attendus=int(acomptes or 0),
        en_retard=int(en_retard or 0),
        stock_bas=sum(1 for ligne in await lignes_de_stock(session) if ligne.alerte),
        sms_en_echec=int(echecs or 0),
        paiements_a_verifier=int(a_verifier or 0),
    )


async def _serie(session: AsyncSession, du: date, au: date) -> tuple[str, list[Point]]:
    """Chiffre d'affaires remis par jour (31 jours au plus) ou par semaine (lundi)."""
    par_jour = (au - du).days + 1 <= JOURS_PAR_POINT_MAX
    debut, fin = _bornes(du, au)
    livree = _etape(Statut.LIVREE)
    periode = cast(func.date_trunc("day" if par_jour else "week", livree.c.le), Date)
    valeurs = {
        jour: (int(chiffre), int(nombre))
        for jour, chiffre, nombre in await session.execute(
            select(periode, func.sum(Commande.total), func.count())
            .select_from(Commande)
            .join(livree, livree.c.commande_id == Commande.id)
            .where(livree.c.le >= debut, livree.c.le < fin)
            .group_by(periode)
        )
    }
    pas = timedelta(days=1 if par_jour else 7)
    point = du if par_jour else du - timedelta(days=du.weekday())
    serie = []
    while point <= au:
        chiffre, nombre = valeurs.get(point, (0, 0))
        serie.append(Point(debut=point, chiffre_affaires=chiffre, commandes=nombre))
        point += pas
    return ("jour" if par_jour else "semaine"), serie


async def tableau_de_bord(
    session: AsyncSession, du: date, au: date, aujourd_hui: date | None = None
) -> TableauDeBord:
    debut, fin = _bornes(du, au)
    pas, serie = await _serie(session, du, au)
    return TableauDeBord.model_validate(
        {
            "du": du,
            "au": au,
            "ventes": await _ventes(session, debut, fin),
            "devis": await _devis(session, debut, fin),
            "delais": await _delais(session, debut, fin),
            "clients": await _clients(session, debut, fin),
            "meilleures_ventes": await _meilleures_ventes(session, debut, fin),
            "alertes": await _alertes(session, aujourd_hui or datetime.now(UTC).date()),
            "pas": pas,
            "serie": serie,
        }
    )
