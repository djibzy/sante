"""Des modèles aux réponses de l'API. Les relations utiles sont chargées par prestations.acces."""

from datetime import date

from prestations import calendrier
from prestations.etats import (
    EN_COURS,
    LIBELLES_COLLECTE,
    LIBELLES_DEMANDE,
    Formule,
    ModeTarif,
    StatutCollecte,
    StatutContrat,
    StatutDemande,
)
from prestations.linge import TYPES_STRUCTURE, Article, Service, TypeStructure, libelle
from prestations.models import Collecte, Contrat, Demande, LigneCollecte, Partenaire
from prestations.schemas import (
    CollecteVue,
    ContratResume,
    ContratVue,
    DemandeVue,
    LigneVue,
    PartenaireResume,
)


def partenaire_resume(partenaire: Partenaire) -> PartenaireResume:
    return PartenaireResume(
        id=partenaire.id,
        nom=partenaire.nom,
        type=partenaire.type,
        est_interne=partenaire.est_interne,
        contact=partenaire.contact,
        telephone=partenaire.telephone,
        quartier=partenaire.quartier,
        delai_jours=partenaire.delai_jours,
        pesee_requise=partenaire.mode_tarif == ModeTarif.KG,
    )


def contrat_resume(contrat: Contrat) -> ContratResume:
    return ContratResume(
        id=contrat.id,
        reference=contrat.reference,
        structure=contrat.structure,
        type_structure=TypeStructure(contrat.type_structure),
        contact=contrat.contact,
        telephone=contrat.telephone,
        adresse=contrat.adresse,
        jours_collecte=list(contrat.jours_collecte),
        libelle_jours=calendrier.jours_en_toutes_lettres(list(contrat.jours_collecte)),
        delai_retour_jours=contrat.delai_retour_jours,
        partenaire=partenaire_resume(contrat.partenaire) if contrat.partenaire else None,
    )


def contrat_vue(contrat: Contrat, demande_reference: str | None = None) -> ContratVue:
    return ContratVue(
        **contrat_resume(contrat).model_dump(),
        service=Service(contrat.service),
        statut=StatutContrat(contrat.statut),
        formule=Formule(contrat.formule),
        tarifs=dict(contrat.tarifs),
        forfait_mensuel=contrat.forfait_mensuel,
        pieces_incluses=contrat.pieces_incluses,
        prix_piece_supplementaire=contrat.prix_piece_supplementaire,
        sms_actifs=contrat.sms_actifs,
        debut_le=contrat.debut_le,
        fin_le=contrat.fin_le,
        notes=contrat.notes,
        demande_reference=demande_reference,
        cree_le=contrat.cree_le,
    )


def demande_vue(demande: Demande, contrat_reference: str | None = None) -> DemandeVue:
    return DemandeVue(
        id=demande.id,
        reference=demande.reference,
        service=Service(demande.service),
        statut=StatutDemande(demande.statut),
        libelle_statut=LIBELLES_DEMANDE[StatutDemande(demande.statut)],
        structure=demande.structure,
        type_structure=TypeStructure(demande.type_structure),
        libelle_type=TYPES_STRUCTURE[TypeStructure(demande.type_structure)],
        contact=demande.contact,
        telephone=demande.telephone,
        quartier=demande.quartier,
        volumes=dict(demande.volumes),
        pieces_par_semaine=sum(demande.volumes.values()),
        collectes_par_semaine=demande.collectes_par_semaine,
        message=demande.message,
        notes_equipe=demande.notes_equipe,
        contrat_reference=contrat_reference,
        cree_le=demande.cree_le,
        modifie_le=demande.modifie_le,
    )


def ligne_vue(ligne: LigneCollecte) -> LigneVue:
    rendue = ligne.quantite_rendue
    return LigneVue(
        article=Article(ligne.article),
        precision=ligne.precision,
        libelle=libelle(Article(ligne.article), ligne.precision),
        quantite_enlevee=ligne.quantite_enlevee,
        quantite_rendue=rendue,
        ecart=None if rendue is None else rendue - ligne.quantite_enlevee,
    )


def manquantes(lignes: list[LigneCollecte]) -> int:
    """Pièces enlevées et pas rendues, article par article (un surplus ne compense pas)."""
    return sum(max(0, ligne.quantite_enlevee - (ligne.quantite_rendue or 0)) for ligne in lignes)


def collecte_vue(collecte: Collecte, jour: date | None = None) -> CollecteVue:
    statut = StatutCollecte(collecte.statut)
    rendue = statut == StatutCollecte.RENDUE
    jour = jour or calendrier.aujourd_hui()
    return CollecteVue(
        id=collecte.id,
        reference=collecte.reference,
        statut=statut,
        libelle_statut=LIBELLES_COLLECTE[statut],
        prevue_le=collecte.prevue_le,
        retour_prevu_le=collecte.retour_prevu_le,
        en_retard=statut in EN_COURS
        and collecte.retour_prevu_le is not None
        and collecte.retour_prevu_le < jour,
        enlevee_le=collecte.enlevee_le,
        deposee_le=collecte.deposee_le,
        prete_le=collecte.prete_le,
        rendue_le=collecte.rendue_le,
        annulee_le=collecte.annulee_le,
        sacs=collecte.sacs,
        poids_kg=float(collecte.poids_kg) if collecte.poids_kg is not None else None,
        remis_par=collecte.remis_par,
        recu_par=collecte.recu_par,
        observations=collecte.observations,
        observations_retour=collecte.observations_retour,
        motif_annulation=collecte.motif_annulation,
        contrat=contrat_resume(collecte.contrat),
        partenaire=partenaire_resume(collecte.partenaire) if collecte.partenaire else None,
        lignes=[ligne_vue(ligne) for ligne in collecte.lignes],
        pieces_enlevees=sum(ligne.quantite_enlevee for ligne in collecte.lignes),
        pieces_rendues=sum(ligne.quantite_rendue or 0 for ligne in collecte.lignes)
        if rendue
        else None,
        pieces_manquantes=manquantes(collecte.lignes) if rendue else None,
    )
