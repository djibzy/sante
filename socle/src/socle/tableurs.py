"""Exports CSV qu'Excel ouvre tel quel : UTF-8 avec BOM, point-virgule, dates jj/mm/aaaa,
montants entiers. Une cellule qui commencerait par = + - @ est neutralisée (injection de
formules dans le tableur du comptable)."""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime

DANGEREUX = ("=", "+", "-", "@", "\t", "\r")


def cellule(valeur: object) -> str | int:
    if valeur is None:
        return ""
    if isinstance(valeur, int):
        return valeur
    if isinstance(valeur, datetime):
        return f"{valeur:%d/%m/%Y}"
    if isinstance(valeur, date):
        return f"{valeur:%d/%m/%Y}"
    texte = str(valeur)
    return f"'{texte}" if texte.startswith(DANGEREUX) else texte


def en_csv(entetes: Sequence[str], lignes: Iterable[Sequence[object]]) -> str:
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
    ecrivain.writerow(entetes)
    for ligne in lignes:
        ecrivain.writerow([cellule(v) for v in ligne])
    return "\ufeff" + tampon.getvalue()  # BOM : Excel reconnaît l'UTF-8
