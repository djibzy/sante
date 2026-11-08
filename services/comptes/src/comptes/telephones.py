"""Numéros de téléphone : l'identifiant de connexion, stocké au format international E.164."""

import phonenumbers


class NumeroInvalide(ValueError):
    pass


def normaliser_telephone(brut: str, region: str = "ML") -> str:
    """« 76 12 34 56 » devient « +22376123456 » ; les numéros étrangers gardent leur indicatif."""
    try:
        numero = phonenumbers.parse(brut, region)
    except phonenumbers.NumberParseException as exc:
        raise NumeroInvalide("Numéro de téléphone invalide") from exc
    if not phonenumbers.is_valid_number(numero):
        raise NumeroInvalide("Numéro de téléphone invalide")
    return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)
