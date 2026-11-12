from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, text

from boutique.entretien import ANONYME, NOM_ANONYME, entretenir
from boutique.models import (
    Avis,
    Commande,
    JournalAudit,
    LigneCommande,
    Notification,
    TransactionPaiement,
)

from .aides import commander, fiche, ligne
from .conftest import jeton

ADMIN = jeton(["boutique:admin"])


async def statut(client: AsyncClient, reference: str, nouveau: str, note: str = "") -> None:
    reponse = await client.post(
        f"/api/v1/admin/commandes/{reference}/statut",
        json={"statut": nouveau, "note": note},
        headers=ADMIN,
    )
    assert reponse.status_code == 200, reponse.text


async def sql(app: FastAPI, requete: str, **valeurs: Any) -> None:
    async with app.state.sessions() as session:
        await session.execute(text(requete), valeurs)
        await session.commit()


def numero(reference: str) -> int:
    return int(reference.removeprefix("BB-"))


async def test_durees_de_conservation(app: FastAPI, client: AsyncClient) -> None:
    brodee = await ligne(client, "blouse-medicale-brodee", "M", personnalisation="Aminata Traoré")
    ancienne = (await commander(client, [brodee]))["commande"]["reference"]
    await statut(client, ancienne, "annulee", note="Cliente partie à Ségou")
    recente = (await commander(client, [brodee], telephone="66 12 34 57"))["commande"]["reference"]
    await statut(client, recente, "annulee")
    facturee = (
        await commander(client, [await ligne(client, "kit-hygiene")], telephone="70 12 34 58")
    )["commande"]["reference"]
    for etape in ("confirmee", "prete", "livree"):
        await statut(client, facturee, etape)
    # L'annulation date de 4 ans ; la commande facturée aussi, mais sa facture est récente.
    for reference in (ancienne, facturee):
        await sql(
            app,
            "UPDATE commandes SET modifie_le = now() - interval '4 years' WHERE numero = :n",
            n=numero(reference),
        )
    await sql(
        app,
        "UPDATE notifications SET cree_le = now() - interval '4 years' "
        "WHERE commande_id = (SELECT id FROM commandes WHERE numero = :n)",
        n=numero(ancienne),
    )
    await sql(
        app,
        "UPDATE journal_audit SET adresse_ip = '196.200.1.1', "
        "cree_le = now() - interval '2 years' WHERE objet_id = :r",
        r=ancienne,
    )

    # Avis refusé il y a 31 jours (effacé) et il y a 10 jours (gardé).
    kit = await fiche(client, "kit-hygiene")
    async with app.state.sessions() as session:
        commande_id = await session.scalar(
            select(Commande.id).where(Commande.numero == numero(facturee))
        )
        maintenant = datetime.now(UTC)
        affiche = await fiche(client, "affiche-a2")
        for jours, produit in ((31, UUID(kit["id"])), (10, UUID(affiche["id"]))):
            session.add(
                Avis(
                    produit_id=produit,
                    commande_id=commande_id,
                    note=1,
                    texte="Avis refusé pour l'essai",
                    auteur="Awa S.",
                    statut="refuse",
                    motif_refus="Information médicale",
                    modere_le=maintenant - timedelta(days=jours),
                )
            )
        for jours in (100, 5):
            session.add(
                TransactionPaiement(
                    commande_id=commande_id,
                    fournisseur="cinetpay",
                    transaction_id=f"ESSAI{jours}",
                    montant=7_500,
                    statut="initiee",
                    cree_le=maintenant - timedelta(days=jours),
                )
            )
        await session.commit()

    bilan = await entretenir(app.state.sessions)
    assert (bilan.commandes, bilan.avis, bilan.tentatives) == (1, 1, 1)
    assert bilan.sms >= 1 and bilan.adresses_ip >= 1

    async with app.state.sessions() as session:
        commandes = {
            c.numero: c for c in await session.scalars(select(Commande).order_by(Commande.numero))
        }
        effacee = commandes[numero(ancienne)]
        assert (effacee.nom_client, effacee.telephone, effacee.adresse) == (
            NOM_ANONYME,
            ANONYME,
            "",
        )
        assert effacee.total > 0  # les montants restent, pour les comptes
        textes = await session.scalars(
            select(LigneCommande.personnalisation).where(LigneCommande.commande_id == effacee.id)
        )
        assert set(textes) == {None}
        assert commandes[numero(recente)].nom_client == "Aminata Traoré"
        assert commandes[numero(facturee)].telephone != ANONYME  # facture de moins de 10 ans
        sms_restants = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.commande_id == effacee.id)
        )
        assert sms_restants == 0
        assert [a.motif_refus for a in await session.scalars(select(Avis))] == [
            "Information médicale"
        ]
        assert list(await session.scalars(select(TransactionPaiement.transaction_id))) == ["ESSAI5"]
        ips = list(
            await session.scalars(
                select(JournalAudit.adresse_ip).where(JournalAudit.objet_id == ancienne)
            )
        )
        assert set(ips) == {None}

    # Facture de plus de 10 ans : la commande est anonymisée à son tour. Rien d'autre ensuite.
    await sql(app, "UPDATE factures SET emise_le = now() - interval '11 years'")
    assert (await entretenir(app.state.sessions)).commandes == 1
    deuxieme = await entretenir(app.state.sessions)
    assert (deuxieme.commandes, deuxieme.sms, deuxieme.avis, deuxieme.tentatives) == (0, 0, 0, 0)
    async with app.state.sessions() as session:
        traces = await session.scalar(
            select(func.count())
            .select_from(JournalAudit)
            .where(JournalAudit.action == "entretien.conservation")
        )
    assert traces == 2  # une trace par passage qui a effacé quelque chose
