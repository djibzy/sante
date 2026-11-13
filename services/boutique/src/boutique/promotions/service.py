"""Codes de réduction : vérifiés au panier (sans le téléphone, encore inconnu), puis de nouveau
à la commande, sous verrou, avec le téléphone (une utilisation par client, nombre maximal).
La réduction porte sur les articles, jamais sur la livraison, et reste un multiple de 5 FCFA
(paiement mobile)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes.cycle import Statut
from boutique.models import CodePromo, Commande

SANS_EFFET = (Statut.ANNULEE, Statut.DEVIS_REFUSE)  # n'utilisent pas le code


class CodeRefuse(Exception):
    """Code inconnu, expiré, épuisé… : le motif est montré au client."""


@dataclass(frozen=True)
class Reduction:
    code: str
    libelle: str
    montant: int


def normaliser(code: str) -> str:
    return code.strip().upper()


def _fcfa(montant: int) -> str:
    return f"{montant:,}".replace(",", " ") + " FCFA"


def montant(code: CodePromo, sous_total: int) -> int:
    brut = sous_total * code.valeur // 100 if code.nature == "pourcentage" else code.valeur
    brut = min(brut, sous_total)
    return brut - brut % 5


async def utilisations(session: AsyncSession, code: str) -> int:
    nombre = await session.scalar(
        select(func.count())
        .select_from(Commande)
        .where(Commande.code_promo == code, Commande.statut.not_in(SANS_EFFET))
    )
    return int(nombre or 0)


async def evaluer(
    session: AsyncSession,
    saisi: str,
    sous_total: int,
    aujourd_hui: date,
    telephone: str | None = None,
    verrouiller: bool = False,
) -> Reduction:
    requete = select(CodePromo).where(CodePromo.code == normaliser(saisi))
    if verrouiller:  # deux commandes simultanées ne dépassent pas le nombre d'utilisations
        requete = requete.with_for_update()
    code = await session.scalar(requete)
    if code is None or not code.est_actif:
        raise CodeRefuse("Ce code n'existe pas.")
    if aujourd_hui < code.debut:
        raise CodeRefuse(f"Ce code est valable à partir du {code.debut:%d/%m/%Y}.")
    if code.fin is not None and aujourd_hui > code.fin:
        raise CodeRefuse("Ce code a expiré.")
    if sous_total < code.minimum:
        raise CodeRefuse(f"Ce code demande {_fcfa(code.minimum)} d'articles au moins.")
    maximum = code.utilisations_max
    if maximum is not None and await utilisations(session, code.code) >= maximum:
        raise CodeRefuse("Ce code a déjà servi autant de fois que prévu.")
    if code.une_fois_par_client and telephone:
        deja = await session.scalar(
            select(
                exists().where(
                    Commande.code_promo == code.code,
                    Commande.telephone == telephone,
                    Commande.statut.not_in(SANS_EFFET),
                )
            )
        )
        if deja:
            raise CodeRefuse("Vous avez déjà utilisé ce code.")
    return Reduction(code.code, code.libelle, montant(code, sous_total))
