"""Ce que l'on prend en charge et pour qui : services proposés, articles de linge, types de
structure. Une liste fermée : les comptes, les tarifs et les relevés se font article par article.
"""

from dataclasses import dataclass
from enum import StrEnum


class Service(StrEnum):
    """Services aux structures. L'entretien du linge ouvre la liste ; les suivants s'y ajoutent."""

    ENTRETIEN_LINGE = "entretien_linge"


SERVICES: dict[Service, str] = {Service.ENTRETIEN_LINGE: "Entretien du linge"}


class Famille(StrEnum):
    TENUES = "tenues"
    LITERIE = "literie"
    TOILETTE = "toilette"
    BLOC = "bloc"
    AUTRES = "autres"


FAMILLES: dict[Famille, str] = {
    Famille.TENUES: "Tenues",
    Famille.LITERIE: "Literie",
    Famille.TOILETTE: "Linge de toilette",
    Famille.BLOC: "Bloc et soins",
    Famille.AUTRES: "Autres",
}


class Article(StrEnum):
    BLOUSE = "blouse"
    TUNIQUE = "tunique"
    PANTALON = "pantalon"
    CASAQUE = "casaque"
    DRAP = "drap"
    ALESE = "alese"
    TAIE = "taie"
    COUVERTURE = "couverture"
    SERVIETTE = "serviette"
    CHAMP = "champ"
    RIDEAU = "rideau"
    AUTRE = "autre"


@dataclass(frozen=True)
class FicheArticle:
    singulier: str
    pluriel: str
    famille: Famille
    note: str = ""


ARTICLES: dict[Article, FicheArticle] = {
    Article.BLOUSE: FicheArticle("blouse", "blouses", Famille.TENUES),
    Article.TUNIQUE: FicheArticle("tunique", "tuniques", Famille.TENUES),
    Article.PANTALON: FicheArticle("pantalon", "pantalons", Famille.TENUES),
    Article.CASAQUE: FicheArticle("casaque de bloc", "casaques de bloc", Famille.TENUES),
    Article.DRAP: FicheArticle("drap", "draps", Famille.LITERIE),
    Article.ALESE: FicheArticle("alèse", "alèses", Famille.LITERIE),
    Article.TAIE: FicheArticle("taie d'oreiller", "taies d'oreiller", Famille.LITERIE),
    Article.COUVERTURE: FicheArticle("couverture", "couvertures", Famille.LITERIE),
    Article.SERVIETTE: FicheArticle("serviette", "serviettes", Famille.TOILETTE),
    Article.CHAMP: FicheArticle(
        "champ opératoire",
        "champs opératoires",
        Famille.BLOC,
        "Lavés et pliés ; la stérilisation reste faite par la structure.",
    ),
    Article.RIDEAU: FicheArticle("rideau", "rideaux", Famille.AUTRES, "Rideaux et paravents."),
    Article.AUTRE: FicheArticle("autre pièce", "autres pièces", Famille.AUTRES, "À préciser."),
}


def nommer(article: Article, quantite: int, precision: str = "") -> str:
    """« 1 drap », « 12 blouses », « 3 nappes » (article « autre » précisé)."""
    fiche = ARTICLES[article]
    if article == Article.AUTRE and precision:
        return f"{quantite} {precision}"
    nom = fiche.singulier if quantite == 1 else fiche.pluriel
    return f"{quantite} {nom}" + (f" ({precision})" if precision else "")


def libelle(article: Article, precision: str = "") -> str:
    """Nom d'une ligne dans un tableau : « Blouse », « Autre pièce : nappes »."""
    nom = ARTICLES[article].singulier
    nom = nom[0].upper() + nom[1:]
    return f"{nom} : {precision}" if precision else nom


class TypeStructure(StrEnum):
    CLINIQUE = "clinique"
    CSCOM = "cscom"
    HOPITAL = "hopital"
    CABINET = "cabinet"
    MATERNITE = "maternite"
    LABORATOIRE = "laboratoire"
    PHARMACIE = "pharmacie"
    ECOLE = "ecole"
    ONG = "ong"
    AUTRE = "autre"


TYPES_STRUCTURE: dict[TypeStructure, str] = {
    TypeStructure.CLINIQUE: "Clinique",
    TypeStructure.CSCOM: "CSCom ou CSRéf",
    TypeStructure.HOPITAL: "Hôpital",
    TypeStructure.CABINET: "Cabinet médical ou dentaire",
    TypeStructure.MATERNITE: "Maternité",
    TypeStructure.LABORATOIRE: "Laboratoire",
    TypeStructure.PHARMACIE: "Pharmacie",
    TypeStructure.ECOLE: "École de santé",
    TypeStructure.ONG: "ONG ou programme de santé",
    TypeStructure.AUTRE: "Autre structure",
}

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def valeurs_sql(enumeration: type[StrEnum]) -> str:
    return ", ".join(f"'{membre.value}'" for membre in enumeration)
