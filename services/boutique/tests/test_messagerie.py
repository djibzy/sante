"""Le fil d'une commande : messages du client et de l'équipe, propositions à accepter, étapes
et paiements au même endroit, images privées, retrait motivé, SMS sans insistance."""

from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient, Response
from PIL import Image
from sqlalchemy import select, text

from boutique.entretien import anonymiser, entretenir
from boutique.models import Commande, JournalAudit, Message, Notification

from .aides import commander, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"], nom="Fatoumata Diarra")
ATELIER = jeton(["boutique:atelier"])
EQUIPE = "+22370000099"


async def commande(client: AsyncClient, **autres: Any) -> tuple[str, str]:
    creee = await commander(client, [await ligne(client, "kit-hygiene")], **autres)
    return creee["commande"]["reference"], creee["cle_suivi"]


async def ecrire(
    client: AsyncClient,
    reference: str,
    texte: str,
    *,
    cle: str | None = None,
    entetes: dict[str, str] | None = None,
    image: bytes | None = None,
    proposition: bool = False,
) -> Response:
    """Par le lien de suivi (cle), le compte du client (entetes), ou l'équipe (ni l'un ni
    l'autre)."""
    if cle:
        chemin, parametres, entetes = f"/api/v1/suivi/{reference}/messages", {"cle": cle}, {}
    elif entetes:
        chemin, parametres = f"/api/v1/mes-commandes/{reference}/messages", {}
    else:
        chemin, parametres, entetes = f"/api/v1/admin/commandes/{reference}/messages", {}, ADMIN
    donnees = {"texte": texte, "proposition": "true"} if proposition else {"texte": texte}
    fichiers = {"image": ("logo.jpg", image, "image/jpeg")} if image else None
    return await client.post(
        chemin, params=parametres, data=donnees, files=fichiers, headers=entetes
    )


async def fil(client: AsyncClient, reference: str, cle: str | None = None) -> Any:
    reponse = (
        await client.get(f"/api/v1/suivi/{reference}/fil", params={"cle": cle})
        if cle
        else await client.get(f"/api/v1/admin/commandes/{reference}/fil", headers=ADMIN)
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


async def sms(app: FastAPI) -> list[tuple[str, str]]:
    async with app.state.sessions() as session:
        notifications = await session.scalars(select(Notification).order_by(Notification.cree_le))
        return [(n.destinataire, n.message) for n in notifications]


async def journal(app: FastAPI) -> list[str]:
    async with app.state.sessions() as session:
        return list(
            await session.scalars(select(JournalAudit.action).order_by(JournalAudit.cree_le))
        )


def photo() -> bytes:
    image = Image.new("RGB", (2400, 1800), (16, 0, 208))
    exif = Image.Exif()
    exif[0x0110] = "Telephone de test"
    tampon = BytesIO()
    image.save(tampon, "JPEG", exif=exif)
    return tampon.getvalue()


async def test_le_fil_reunit_messages_etapes_et_paiements(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.parametres.telephones_equipe = [EQUIPE]
    reference, cle = await commande(client)
    await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": "confirmee", "note": "Stock vérifié", "visible_client": False},
        headers=ADMIN,
    )
    question = await ecrire(client, reference, "  Puis-je passer samedi matin ?  ", cle=cle)
    assert question.status_code == 201, question.text
    assert question.json()["texte"] == "Puis-je passer samedi matin ?"
    await client.post(
        f"/api/v1/admin/commandes/{reference}/paiements",
        json={"montant": 5_000, "moyen": "orange_money"},
        headers=ADMIN,
    )
    reponse = await ecrire(client, reference, "Oui, nous ouvrons à 8 h.")
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["nom_auteur"] == "Fatoumata Diarra"

    cote_client = await fil(client, reference, cle)
    assert [(e["type"], e["libelle"] or e["texte"]) for e in cote_client["entrees"]] == [
        ("etape", "Reçue, à confirmer"),
        ("message", "Puis-je passer samedi matin ?"),
        ("paiement", "Paiement reçu (Orange Money)"),
        ("message", "Oui, nous ouvrons à 8 h."),
    ]
    assert cote_client["entrees"][2]["montant"] == 5_000
    assert cote_client["entrees"][3]["nom_auteur"] == ""  # le client lit « la boutique »
    assert cote_client["ouvert"] is True and cote_client["a_lire"] == 1

    cote_equipe = await fil(client, reference)
    etapes = [e for e in cote_equipe["entrees"] if e["type"] == "etape"]
    assert [(e["libelle"], e["note"], e["interne"]) for e in etapes] == [
        ("Reçue, à confirmer", "", False),
        ("Confirmée", "Stock vérifié", True),  # étape interne : l'équipe seule la voit
    ]
    # Répondre, c'est avoir lu : le message du client est marqué lu, plus rien à lire.
    assert cote_equipe["a_lire"] == 0
    assert cote_equipe["entrees"][2]["lu_le"] is not None

    # Le client ouvre le fil : la réponse de la boutique est lue à son tour.
    lu = await client.post(f"/api/v1/suivi/{reference}/messages/lecture", params={"cle": cle})
    assert lu.status_code == 204
    assert (await fil(client, reference, cle))["a_lire"] == 0
    assert (await fil(client, reference))["entrees"][-1]["lu_le"] is not None

    messages = [m for m in await sms(app) if "message" in m[1]]
    assert messages == [
        (EQUIPE, f"Bibou : message d'un client sur la commande {reference}. A lire dans Gestion."),
        (
            "+22376123456",
            f"Bibou : un message vous attend pour la commande {reference}. Lisez-le et "
            "répondez depuis votre lien de suivi.",
        ),
    ]


async def test_les_sms_n_insistent_pas(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.telephones_equipe = [EQUIPE]
    reference, cle = await commande(client)

    async def nombre(destinataire: str) -> int:
        return sum(
            1 for numero, texte in await sms(app) if numero == destinataire and "message" in texte
        )

    for texte in ("Bonjour", "Votre broderie est prête à valider.", "Rappelez-nous si besoin."):
        assert (await ecrire(client, reference, texte)).status_code == 201
    assert await nombre("+22376123456") == 1  # un seul SMS tant que le client n'a rien lu
    await client.post(f"/api/v1/suivi/{reference}/messages/lecture", params={"cle": cle})
    await ecrire(client, reference, "Autre chose : la couleur du fil.")
    assert await nombre("+22376123456") == 2  # il a lu : le message suivant le prévient

    for texte in ("Merci", "Je passe demain", "Vers 10 h"):
        assert (await ecrire(client, reference, texte, cle=cle)).status_code == 201
    assert await nombre(EQUIPE) == 1
    # Un jour sans lecture : un rappel repart.
    async with app.state.sessions() as session:
        await session.execute(text("UPDATE messages SET cree_le = cree_le - interval '25 hours'"))
        await session.commit()
    await ecrire(client, reference, "Êtes-vous ouverts ?", cle=cle)
    assert await nombre(EQUIPE) == 2


async def test_une_proposition_acceptee_fait_foi(app: FastAPI, client: AsyncClient) -> None:
    app.state.parametres.telephones_equipe = [EQUIPE]
    reference, cle = await commande(client)
    proposee = await ecrire(
        client,
        reference,
        "Broderie « Dr Awa Traoré – Pédiatrie » en bleu marine, poitrine gauche, 8 cm.",
        proposition=True,
    )
    assert proposee.status_code == 201, proposee.text
    proposition = proposee.json()
    assert (proposition["type"], proposition["etat"]) == ("proposition", "en_attente")
    assert (await fil(client, reference, cle))["propositions_en_attente"] == 1
    assert (await sms(app))[-1] == (
        "+22376123456",
        f"Bibou : une proposition attend votre accord pour la commande {reference}. "
        "Acceptez-la ou refusez-la depuis votre lien de suivi.",
    )

    # Le client n'écrit pas de proposition : son message reste un message.
    simple = await client.post(
        f"/api/v1/suivi/{reference}/messages",
        params={"cle": cle},
        data={"texte": "D'accord sur le principe", "proposition": "true"},
    )
    assert simple.json()["type"] == "message"

    chemin = f"/api/v1/suivi/{reference}/propositions/{proposition['id']}/reponse"
    acceptee = await client.post(chemin, params={"cle": cle}, json={"accepte": True})
    assert acceptee.status_code == 200, acceptee.text
    assert acceptee.json()["etat"] == "acceptee" and acceptee.json()["repondue_le"]
    assert acceptee.json()["libelle_etat"] == "Acceptée"
    assert (await sms(app))[-1] == (
        EQUIPE,
        f"Bibou : proposition acceptée par le client, commande {reference}.",
    )
    assert "proposition.acceptee" in await journal(app)
    deux_fois = await client.post(chemin, params={"cle": cle}, json={"accepte": False})
    assert deux_fois.status_code == 409
    # Ce qui est accepté ne se retire plus, même par l'équipe.
    retrait = await client.post(
        f"/api/v1/admin/commandes/{reference}/messages/{proposition['id']}/retrait",
        json={"motif": "Erreur de saisie"},
        headers=ADMIN,
    )
    assert retrait.status_code == 409
    assert retrait.json()["detail"] == "Une proposition acceptée fait foi : elle ne se retire pas"

    # Refuser ; puis une proposition annulée par l'équipe ne s'accepte plus.
    seconde = (
        await ecrire(client, reference, "Livraison le 28 au lieu du 25.", proposition=True)
    ).json()
    refusee = await client.post(
        f"/api/v1/suivi/{reference}/propositions/{seconde['id']}/reponse",
        params={"cle": cle},
        json={"accepte": False},
    )
    assert refusee.json()["etat"] == "refusee"
    troisieme = (await ecrire(client, reference, "Livraison le 27.", proposition=True)).json()
    annulee = await client.post(
        f"/api/v1/admin/commandes/{reference}/propositions/{troisieme['id']}/annulation",
        headers=ADMIN,
    )
    assert annulee.status_code == 200 and annulee.json()["etat"] == "annulee"
    assert annulee.json()["texte"] == "Livraison le 27."  # le texte reste dans le fil
    trop_tard = await client.post(
        f"/api/v1/suivi/{reference}/propositions/{troisieme['id']}/reponse",
        params={"cle": cle},
        json={"accepte": True},
    )
    assert trop_tard.status_code == 409
    assert (await fil(client, reference, cle))["propositions_en_attente"] == 0

    # Commande annulée : il n'y a plus rien à accepter.
    quatrieme = (await ecrire(client, reference, "Retrait lundi matin.", proposition=True)).json()
    await client.post(
        f"/api/v1/admin/commandes/{reference}/statut", json={"statut": "annulee"}, headers=ADMIN
    )
    apres_annulation = await client.post(
        f"/api/v1/suivi/{reference}/propositions/{quatrieme['id']}/reponse",
        params={"cle": cle},
        json={"accepte": True},
    )
    assert apres_annulation.status_code == 409
    assert [action for action in await journal(app) if action.startswith("proposition.")] == [
        "proposition.acceptee",
        "proposition.refusee",
        "proposition.annulee",
    ]


async def test_image_privee_puis_message_retire(app: FastAPI, client: AsyncClient) -> None:
    reference, cle = await commande(client)
    envoi = await ecrire(client, reference, "Notre logo", cle=cle, image=photo())
    assert envoi.status_code == 201, envoi.text
    message = envoi.json()
    assert message["image"] is True
    chemin = f"/api/v1/suivi/{reference}/messages/{message['id']}/image"

    vue = await client.get(chemin, params={"cle": cle})
    assert vue.status_code == 200
    assert vue.headers["content-type"] == "image/webp"
    assert vue.headers["cache-control"].startswith("private")
    with Image.open(BytesIO(vue.content)) as image:
        assert max(image.size) == 1600 and not image.getexif()  # réduite, sans métadonnée
    assert (await client.get(chemin)).status_code == 404  # sans la clé
    assert (await client.get(chemin, params={"cle": "x" * 24})).status_code == 404
    equipe = await client.get(
        f"/api/v1/admin/commandes/{reference}/messages/{message['id']}/image", headers=ADMIN
    )
    assert equipe.status_code == 200

    # Le fichier est sur le disque, hors du dossier public.
    dossier = Path(app.state.parametres.dossier_medias) / "messages"
    [fichier] = list(dossier.iterdir())
    assert (await client.get(f"/medias/messages/{fichier.name}")).status_code == 404

    # Seules les images passent, et pas trop lourdes.
    document = await client.post(
        f"/api/v1/suivi/{reference}/messages",
        params={"cle": cle},
        data={"texte": "Ordonnance"},
        files={"image": ("ordonnance.pdf", b"%PDF-1.4 ...", "application/pdf")},
    )
    assert document.status_code == 422
    app.state.parametres.taille_max_photo = 1_000
    lourde = await ecrire(client, reference, "Photo", cle=cle, image=photo())
    assert lourde.status_code == 413
    assert len(list(dossier.iterdir())) == 1  # rien d'autre n'a été gardé

    # L'équipe retire le message : texte et image disparaissent, le retrait reste tracé.
    retrait = await client.post(
        f"/api/v1/admin/commandes/{reference}/messages/{message['id']}/retrait",
        json={"motif": "Information de santé d'un patient"},
        headers=ADMIN,
    )
    assert retrait.status_code == 200, retrait.text
    retire = retrait.json()
    assert (retire["texte"], retire["image"], retire["retire"]) == ("", False, True)
    assert retire["motif_retrait"] == "Information de santé d'un patient"
    assert list(dossier.iterdir()) == []
    assert (await client.get(chemin, params={"cle": cle})).status_code == 404
    encore = await client.post(
        f"/api/v1/admin/commandes/{reference}/messages/{message['id']}/retrait",
        json={"motif": "Deux fois"},
        headers=ADMIN,
    )
    assert encore.status_code == 409
    assert (await journal(app))[-1] == "message.retire"
    vu_du_client = (await fil(client, reference, cle))["entrees"][-1]
    assert (vu_du_client["retire"], vu_du_client["texte"]) == (True, "")


async def test_acces_et_limites(app: FastAPI, client: AsyncClient) -> None:
    awa = jeton(nom="Awa Traoré")
    reference, cle = await commande(client, entetes=awa)
    autre, cle_autre = await commande(client, telephone="66 77 88 99")

    # Le compte qui a commandé écrit sans la clé ; un autre compte ne voit rien.
    depuis_le_compte = await ecrire(client, reference, "Bonjour", entetes=awa)
    assert depuis_le_compte.status_code == 201
    assert (
        await client.get(f"/api/v1/mes-commandes/{reference}/fil", headers=awa)
    ).status_code == 200
    intrus = jeton(nom="Quelqu'un d'autre")
    assert (
        await client.get(f"/api/v1/mes-commandes/{reference}/fil", headers=intrus)
    ).status_code == 404
    assert (await client.get(f"/api/v1/mes-commandes/{reference}/fil")).status_code == 401
    # La clé d'une autre commande n'ouvre pas ce fil.
    assert (
        await client.get(f"/api/v1/suivi/{reference}/fil", params={"cle": cle_autre})
    ).status_code == 404
    assert (await ecrire(client, reference, "Intrus", cle=cle_autre)).status_code == 404
    # La gestion seulement, pas l'atelier ; et un message d'une autre commande est introuvable.
    assert (
        await client.get(f"/api/v1/admin/commandes/{reference}/fil", headers=ATELIER)
    ).status_code == 403
    message = depuis_le_compte.json()
    ailleurs = await client.post(
        f"/api/v1/admin/commandes/{autre}/messages/{message['id']}/retrait",
        json={"motif": "Mauvaise commande"},
        headers=ADMIN,
    )
    assert ailleurs.status_code == 404

    assert (await ecrire(client, reference, "   ", cle=cle)).status_code == 422
    assert (await ecrire(client, reference, "x" * 2001, cle=cle)).status_code == 422
    trop_courte = await ecrire(client, reference, "Ok ?", proposition=True)
    assert trop_courte.status_code == 422

    async with app.state.sessions() as session:
        compte = await session.scalar(select(Message.auteur_id).where(Message.id == message["id"]))
        assert compte is not None  # le compte du client est gardé avec son message
        commande_id = await session.scalar(
            select(Commande.id).where(Commande.numero == int(reference[3:]))
        )
        session.add_all(
            Message(commande_id=commande_id, auteur="client", texte=f"Message {i}")
            for i in range(19)
        )
        await session.commit()
    de_trop = await ecrire(client, reference, "Encore un", cle=cle)
    assert de_trop.status_code == 429
    assert "appelez-nous" in de_trop.json()["detail"]

    # Commande archivée (anonymisée) : le fil est vide et fermé.
    async with app.state.sessions() as session:
        await anonymiser(session, [commande_id])
        await session.commit()
    ferme = await fil(client, reference)
    assert ferme["ouvert"] is False
    assert [e for e in ferme["entrees"] if e["type"] == "message"] == []
    assert (await ecrire(client, reference, "Bonjour")).status_code == 409


async def test_file_de_la_gestion_et_alertes(client: AsyncClient) -> None:
    awa = jeton(nom="Awa Traoré")
    avec_message, cle = await commande(client, entetes=awa)
    sans_message, _ = await commande(client, telephone="66 77 88 99")
    await ecrire(client, avec_message, "Une question sur la taille", cle=cle)
    await ecrire(client, avec_message, "Et sur la couleur", cle=cle)

    file = (await client.get("/api/v1/admin/commandes", headers=ADMIN)).json()["elements"]
    assert {c["reference"]: c["messages_a_lire"] for c in file} == {
        avec_message: 2,
        sans_message: 0,
    }
    a_lire = await client.get(
        "/api/v1/admin/commandes", params={"messages_a_lire": "true"}, headers=ADMIN
    )
    assert [c["reference"] for c in a_lire.json()["elements"]] == [avec_message]
    tableau = (await client.get("/api/v1/admin/tableau-de-bord", headers=ADMIN)).json()
    assert tableau["alertes"]["messages_a_lire"] == 1

    # L'équipe ouvre le fil puis répond : plus rien à lire pour elle, un message pour le client.
    lecture = await client.post(
        f"/api/v1/admin/commandes/{avec_message}/messages/lecture", headers=ADMIN
    )
    assert lecture.status_code == 204
    await ecrire(client, avec_message, "Prenez votre taille habituelle.")
    tableau = (await client.get("/api/v1/admin/tableau-de-bord", headers=ADMIN)).json()
    assert tableau["alertes"]["messages_a_lire"] == 0
    miennes = (await client.get("/api/v1/mes-commandes", headers=awa)).json()
    assert [(c["reference"], c["messages_a_lire"]) for c in miennes] == [(avec_message, 1)]


async def test_conservation_et_donnees_personnelles(app: FastAPI, client: AsyncClient) -> None:
    awa = jeton(nom="Awa Traoré")
    reference, cle = await commande(client, entetes=awa)
    await ecrire(client, reference, "Voici notre logo", cle=cle, image=photo())
    accord = (
        await ecrire(client, reference, "Broderie en fil doré, 8 cm.", proposition=True)
    ).json()
    await client.post(
        f"/api/v1/suivi/{reference}/propositions/{accord['id']}/reponse",
        params={"cle": cle},
        json={"accepte": True},
    )
    await ecrire(client, reference, "Merci, à bientôt.")

    export = (await client.get("/api/v1/mes-donnees", headers=awa)).json()
    assert [
        (m["commande"], m["auteur"], m["texte"], m["proposition"]) for m in export["messages"]
    ] == [
        (reference, "vous", "Voici notre logo", None),
        (reference, "la boutique", "Broderie en fil doré, 8 cm.", "acceptee"),
        (reference, "la boutique", "Merci, à bientôt.", None),
    ]
    assert export["messages"][0]["image_jointe"] is True

    # Affaire finie depuis plus de trois ans : les messages partent, l'accord reste.
    for etape in ("confirmee", "prete", "livree"):
        await client.post(
            f"/api/v1/admin/commandes/{reference}/statut", json={"statut": etape}, headers=ADMIN
        )
    dossier = Path(app.state.parametres.dossier_medias)
    assert (await entretenir(app.state.sessions, dossier_medias=dossier)).messages == 0
    async with app.state.sessions() as session:
        await session.execute(text("UPDATE commandes SET statut_le = now() - interval '4 years'"))
        await session.commit()
    bilan = await entretenir(app.state.sessions, dossier_medias=dossier)
    assert bilan.messages == 2
    assert list((dossier / "messages").iterdir()) == []
    restants = [e for e in (await fil(client, reference))["entrees"] if e["type"] != "etape"]
    assert [(e["type"], e["etat"]) for e in restants] == [("proposition", "acceptee")]
    assert (await entretenir(app.state.sessions, dossier_medias=dossier)).messages == 0
