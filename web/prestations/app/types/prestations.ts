/** Réponses de l'API Prestations (voir services/prestations/src/prestations/schemas.py). */

export interface Choix { code: string; libelle: string }

export interface ArticleOffre {
  code: string
  libelle: string
  pluriel: string
  famille: string
  libelle_famille: string
  note: string
}

export interface Offre {
  services: Choix[]
  articles: ArticleOffre[]
  types_structure: Choix[]
}

export type StatutDemande = 'nouvelle' | 'en_discussion' | 'signee' | 'sans_suite'

export interface Demande {
  id: string
  reference: string
  service: string
  statut: StatutDemande
  libelle_statut: string
  structure: string
  type_structure: string
  libelle_type: string
  contact: string
  telephone: string
  quartier: string
  volumes: Record<string, number>
  pieces_par_semaine: number
  collectes_par_semaine: number | null
  message: string
  notes_equipe: string
  contrat_reference: string | null
  cree_le: string
  modifie_le: string
}

export interface PageDemandes { elements: Demande[]; total: number; nouvelles: number }

export type ModeTarif = 'piece' | 'kg'

export interface PartenaireResume {
  id: string
  nom: string
  type: 'blanchisserie' | 'pressing'
  est_interne: boolean
  contact: string
  telephone: string
  quartier: string
  delai_jours: number
  pesee_requise: boolean
}

export interface Partenaire extends Omit<PartenaireResume, 'pesee_requise'> {
  capacite_pieces_jour: number | null
  mode_tarif: ModeTarif
  tarifs: Record<string, number>
  tarif_kg: number | null
  hygiene_verifiee_le: string | null
  notes: string
  est_actif: boolean
  cree_le: string
}

export interface ContratResume {
  id: string
  reference: string
  structure: string
  type_structure: string
  contact: string
  telephone: string
  adresse: string
  jours_collecte: number[]
  libelle_jours: string
  delai_retour_jours: number
  partenaire: PartenaireResume | null
}

export type Formule = 'piece' | 'forfait'
export type StatutContrat = 'actif' | 'suspendu' | 'termine'

export interface Contrat extends ContratResume {
  service: string
  statut: StatutContrat
  formule: Formule
  tarifs: Record<string, number>
  forfait_mensuel: number | null
  pieces_incluses: number | null
  prix_piece_supplementaire: number | null
  sms_actifs: boolean
  debut_le: string
  fin_le: string | null
  notes: string
  demande_reference: string | null
  cree_le: string
}

export type StatutCollecte = 'prevue' | 'enlevee' | 'chez_partenaire' | 'prete' | 'rendue' | 'annulee'

export interface LigneCollecte {
  article: string
  precision: string
  libelle: string
  quantite_enlevee: number
  quantite_rendue: number | null
  ecart: number | null
}

export interface Collecte {
  id: string
  reference: string
  statut: StatutCollecte
  libelle_statut: string
  prevue_le: string
  retour_prevu_le: string | null
  en_retard: boolean
  enlevee_le: string | null
  deposee_le: string | null
  prete_le: string | null
  rendue_le: string | null
  annulee_le: string | null
  sacs: number | null
  poids_kg: number | null
  remis_par: string
  recu_par: string
  observations: string
  observations_retour: string
  motif_annulation: string
  contrat: ContratResume
  partenaire: PartenaireResume | null
  lignes: LigneCollecte[]
  pieces_enlevees: number
  pieces_rendues: number | null
  pieces_manquantes: number | null
}

export interface PageCollectes { elements: Collecte[]; total: number }

export interface Passage {
  contrat: ContratResume
  collecte: Collecte | null
  au_calendrier: boolean
}

export interface Tournee {
  jour: string
  libelle_jour: string
  passages: Passage[]
  a_deposer: Collecte[]
  a_rendre: Collecte[]
}

export interface LigneReleve {
  article: string
  libelle: string
  prix_unitaire: number | null
  enlevees: number
  rendues: number
  manquantes: number
  montant: number
}

export interface SyntheseContrat {
  reference: string
  structure: string
  formule: Formule
  collectes: number
  pieces_rendues: number
  pieces_manquantes: number
  chiffre: number
  cout: number
  marge: number
  cout_incomplet: boolean
  prix_manquants: boolean
}

export interface SynthesePartenaire {
  id: string
  nom: string
  mode_tarif: ModeTarif
  collectes: number
  pieces: number
  poids_kg: number
  cout: number
  cout_incomplet: boolean
}

export interface Synthese {
  mois: string
  libelle_mois: string
  contrats: SyntheseContrat[]
  partenaires: SynthesePartenaire[]
  chiffre: number
  cout: number
  marge: number
  pieces_rendues: number
  pieces_manquantes: number
  en_cours: number
}

/** Pastille d'un statut de collecte (classes de la charte). */
export function classeCollecte(statut: StatutCollecte, enRetard = false): string {
  if (enRetard) return 'pastille pastille-danger'
  return {
    prevue: 'pastille pastille-attente',
    enlevee: 'pastille',
    chez_partenaire: 'pastille',
    prete: 'pastille pastille-accent',
    rendue: 'pastille pastille-succes',
    annulee: 'pastille pastille-attente',
  }[statut]
}
