"""Mise en forme des commandes pour le client et pour l'équipe."""

from boutique.commandes import acompte
from boutique.commandes.cycle import ANNULABLES_PAR_CLIENT, LIBELLES, PASSAGES, Statut
from boutique.commandes.schemas import (
    CommandeClient,
    CommandeGestion,
    CommandeResume,
    EvenementGestion,
    EvenementVue,
    LigneVue,
    PaiementVue,
)
from boutique.commandes.tarifs import aujourd_hui
from boutique.models import Commande

DEVIS = frozenset({Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE, Statut.DEVIS_REFUSE})


def devis_expire(commande: Commande) -> bool:
    fin = commande.devis_valable_jusqu_au
    return fin is not None and aujourd_hui() > fin


def _champs_communs(commande: Commande) -> dict[str, object]:
    statut = Statut(commande.statut)
    return {
        "reference": commande.reference,
        "statut": statut,
        "statut_libelle": LIBELLES[statut],
        "est_devis": statut in DEVIS,
        "cree_le": commande.cree_le,
        "nom_client": commande.nom_client,
        "telephone": commande.telephone,
        "etablissement": commande.etablissement,
        "mode_livraison": commande.mode_livraison,
        "date_promise": commande.date_promise,
        "total": commande.total,
        "montant_paye": commande.montant_paye,
    }


def vue_client(commande: Commande) -> CommandeClient:
    statut = Statut(commande.statut)
    return CommandeClient(
        **_champs_communs(commande),
        zone_nom=commande.zone.nom if commande.zone else None,
        adresse=commande.adresse,
        mode_paiement=commande.mode_paiement,
        lignes=[LigneVue.model_validate(ligne) for ligne in commande.lignes],
        sous_total=commande.sous_total,
        frais_livraison=commande.frais_livraison,
        remise=commande.remise,
        reste_a_payer=commande.reste_a_payer,
        acompte=commande.acompte,
        acompte_restant=acompte.restant(commande),
        acompte_garde=commande.acompte_garde,
        code_promo=commande.code_promo,
        devis_valable_jusqu_au=commande.devis_valable_jusqu_au,
        devis_disponible=commande.devis_emis_le is not None,
        facture=commande.facture.reference if commande.facture else None,
        livreur_nom=commande.livreur.nom if commande.livreur else None,
        livreur_telephone=commande.livreur.telephone if commande.livreur else None,
        peut_annuler=statut in ANNULABLES_PAR_CLIENT,
        peut_accepter=statut == Statut.DEVIS_ENVOYE and not devis_expire(commande),
        historique=[
            EvenementVue(
                statut=Statut(e.statut),
                libelle=LIBELLES[Statut(e.statut)],
                note=e.note,
                cree_le=e.cree_le,
            )
            for e in commande.evenements
            if e.visible_client
        ],
    )


def vue_gestion(commande: Commande) -> CommandeGestion:
    client = vue_client(commande)
    return CommandeGestion(
        **client.model_dump(),
        id=commande.id,
        client_id=commande.client_id,
        email=commande.email,
        note_client=commande.note_client,
        tarif_professionnel=commande.tarif_professionnel,
        devis_emis_le=commande.devis_emis_le,
        paiements=[PaiementVue.model_validate(p) for p in commande.paiements],
        historique_complet=[
            EvenementGestion(
                statut=Statut(e.statut),
                libelle=LIBELLES[Statut(e.statut)],
                note=e.note,
                cree_le=e.cree_le,
                visible_client=e.visible_client,
                acteur_id=e.acteur_id,
            )
            for e in commande.evenements
        ],
        passages_possibles=[s for s in Statut if s in PASSAGES[Statut(commande.statut)]],
    )


def vue_resume(commande: Commande, zone_nom: str | None, nombre_articles: int) -> CommandeResume:
    return CommandeResume(
        **_champs_communs(commande),
        zone_nom=zone_nom,
        nombre_articles=nombre_articles,
    )
