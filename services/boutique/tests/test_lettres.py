import pytest

from boutique.commandes.lettres import en_lettres, francs_cfa


@pytest.mark.parametrize(
    ("nombre", "texte"),
    [
        (0, "zéro"),
        (1, "un"),
        (16, "seize"),
        (17, "dix-sept"),
        (21, "vingt et un"),
        (22, "vingt-deux"),
        (71, "soixante et onze"),
        (77, "soixante-dix-sept"),
        (80, "quatre-vingts"),
        (81, "quatre-vingt-un"),
        (91, "quatre-vingt-onze"),
        (100, "cent"),
        (101, "cent un"),
        (200, "deux cents"),
        (280, "deux cent quatre-vingts"),
        (1000, "mille"),
        (1500, "mille cinq cents"),
        (12_500, "douze mille cinq cents"),
        (80_000, "quatre-vingt mille"),
        (200_000, "deux cent mille"),
        (1_000_000, "un million"),
        (2_500_000, "deux millions cinq cent mille"),
        (80_000_000, "quatre-vingts millions"),
        (1_000_000_000, "un milliard"),
    ],
)
def test_en_lettres(nombre: int, texte: str) -> None:
    assert en_lettres(nombre) == texte


def test_francs_cfa() -> None:
    assert francs_cfa(700_000) == "sept cent mille francs CFA"
    assert francs_cfa(1_000_000) == "un million de francs CFA"
    assert francs_cfa(13_500) == "treize mille cinq cents francs CFA"
