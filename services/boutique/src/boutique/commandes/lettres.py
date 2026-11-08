"""Montants en toutes lettres, pour la formule « Arrêté le présent devis à la somme de… ».

Orthographe traditionnelle : traits d'union sous cent, « et » pour 21, 31… 71, accord de
« vingt » et « cent » quand ils terminent le nombre ou précèdent « million(s) ».
"""

_UNITES = [
    "zéro",
    "un",
    "deux",
    "trois",
    "quatre",
    "cinq",
    "six",
    "sept",
    "huit",
    "neuf",
    "dix",
    "onze",
    "douze",
    "treize",
    "quatorze",
    "quinze",
    "seize",
    "dix-sept",
    "dix-huit",
    "dix-neuf",
]
_DIZAINES = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"}


def _moins_de_cent(n: int) -> str:
    if n < 20:
        return _UNITES[n]
    dizaine, unite = divmod(n, 10)
    if dizaine in (7, 9):  # soixante-dix, quatre-vingt-dix : on compte de 10 à 19
        base = "soixante" if dizaine == 7 else "quatre-vingt"
        reste = unite + 10
        liaison = " et " if (dizaine == 7 and unite == 1) else "-"
        return f"{base}{liaison}{_UNITES[reste]}"
    if dizaine == 8:
        return "quatre-vingts" if unite == 0 else f"quatre-vingt-{_UNITES[unite]}"
    mot = _DIZAINES[dizaine]
    if unite == 0:
        return mot
    if unite == 1:
        return f"{mot} et un"
    return f"{mot}-{_UNITES[unite]}"


def _moins_de_mille(n: int, final: bool) -> str:
    """`final` : le groupe termine le nombre ou précède « million(s) » (accord du pluriel)."""
    centaines, reste = divmod(n, 100)
    mots = []
    if centaines:
        if centaines == 1:
            mots.append("cent")
        else:
            mots.append(f"{_UNITES[centaines]} cent" + ("s" if reste == 0 and final else ""))
    if reste:
        texte = _moins_de_cent(reste)
        if not final and texte.endswith("quatre-vingts"):
            texte = texte[:-1]
        mots.append(texte)
    return " ".join(mots)


def en_lettres(n: int) -> str:
    if n < 0:
        return "moins " + en_lettres(-n)
    if n == 0:
        return "zéro"
    milliards, reste = divmod(n, 1_000_000_000)
    millions, reste = divmod(reste, 1_000_000)
    milliers, unites = divmod(reste, 1000)
    mots = []
    if milliards:
        mots.append(f"{_moins_de_mille(milliards, True)} milliard" + ("s" if milliards > 1 else ""))
    if millions:
        mots.append(f"{_moins_de_mille(millions, True)} million" + ("s" if millions > 1 else ""))
    if milliers:
        mots.append("mille" if milliers == 1 else f"{_moins_de_mille(milliers, False)} mille")
    if unites:
        mots.append(_moins_de_mille(unites, True))
    return " ".join(mots)


def francs_cfa(n: int) -> str:
    """« douze mille cinq cents francs CFA » ; « un million de francs CFA »."""
    texte = en_lettres(n)
    de = "de " if n and n % 1_000_000 == 0 else ""
    return f"{texte} {de}francs CFA"
