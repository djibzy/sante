import httpx

from socle.surveillance import Surveillant, controler


class Boite:
    def __init__(self) -> None:
        self.envoyes: list[tuple[str, str]] = []

    async def envoyer(self, destinataire: str, message: str) -> str | None:
        self.envoyes.append((destinataire, message))
        return None


async def test_alerte_apres_plusieurs_echecs_puis_retablissement() -> None:
    boite = Boite()
    s = Surveillant(["+22370000000", "+22371000000"], boite, echecs_avant_alerte=3)
    adresse = "https://boutique.exemple.ml/sante"
    await s.noter(adresse, False, 0)
    await s.noter(adresse, False, 60)
    assert boite.envoyes == []  # deux ratés de suite : pas d'alerte
    await s.noter(adresse, False, 120)
    assert [n for n, _ in boite.envoyes] == ["+22370000000", "+22371000000"]
    assert "boutique.exemple.ml ne repond plus" in boite.envoyes[0][1]
    await s.noter(adresse, False, 180)
    assert len(boite.envoyes) == 2  # une seule alerte par panne
    await s.noter(adresse, True, 420)
    assert len(boite.envoyes) == 4
    assert "fonctionne de nouveau (5 min)" in boite.envoyes[2][1]


async def test_un_rate_isole_ne_previent_personne() -> None:
    boite = Boite()
    s = Surveillant(["+22370000000"], boite, echecs_avant_alerte=3)
    for bon in (False, False, True, False, False, True):
        await s.noter("https://a.ml/sante", bon, 0)
    assert boite.envoyes == []


async def test_un_sms_qui_echoue_n_arrete_pas_la_surveillance() -> None:
    class Casse:
        async def envoyer(self, destinataire: str, message: str) -> str | None:
            raise RuntimeError("fournisseur indisponible")

    s = Surveillant(["+22370000000"], Casse(), echecs_avant_alerte=1)
    await s.noter("https://a.ml/sante", False, 0)
    assert s.etats["https://a.ml/sante"].en_panne


async def test_controle_du_service() -> None:
    def repondre(requete: httpx.Request) -> httpx.Response:
        if requete.url.host == "bon.ml":
            return httpx.Response(200, json={"statut": "ok", "service": "boutique"})
        if requete.url.host == "base.ml":
            return httpx.Response(500)
        raise httpx.ConnectError("injoignable")

    async with httpx.AsyncClient(transport=httpx.MockTransport(repondre)) as client:
        assert await controler(client, "https://bon.ml/sante")
        assert not await controler(client, "https://base.ml/sante")
        assert not await controler(client, "https://mort.ml/sante")
