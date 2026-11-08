export type Statut =
  | 'devis_demande' | 'devis_envoye' | 'devis_refuse' | 'en_attente' | 'confirmee'
  | 'en_preparation' | 'prete' | 'en_livraison' | 'livree' | 'annulee'

export type ModeLivraison = 'retrait' | 'livraison'

export interface Zone {
  id: string
  slug: string
  nom: string
  frais: number
  delai_jours: number
}

export interface LigneChiffree {
  produit_id: string
  variante_id: string | null
  produit_slug: string | null
  libelle: string
  quantite: number
  prix_unitaire: number | null
  montant: number
  personnalisation: string | null
  commandable: boolean
  motif: string | null
}

export interface Chiffrage {
  lignes: LigneChiffree[]
  sous_total: number
  frais_livraison: number
  total: number
  date_estimee: string
  commandable: boolean
}

export interface LigneCommande {
  id: string
  produit_id: string | null
  variante_id: string | null
  libelle: string
  sku: string | null
  quantite: number
  prix_unitaire: number
  montant: number
  personnalisation: string | null
}

export interface Evenement {
  statut: Statut
  libelle: string
  note: string
  cree_le: string
}

export interface Commande {
  reference: string
  statut: Statut
  statut_libelle: string
  est_devis: boolean
  cree_le: string
  nom_client: string
  telephone: string
  etablissement: string | null
  mode_livraison: ModeLivraison
  zone_nom: string | null
  adresse: string
  lignes: LigneCommande[]
  sous_total: number
  frais_livraison: number
  remise: number
  total: number
  montant_paye: number
  reste_a_payer: number
  date_promise: string | null
  devis_valable_jusqu_au: string | null
  devis_disponible: boolean
  peut_annuler: boolean
  peut_accepter: boolean
  historique: Evenement[]
}

export interface CommandeCreee {
  commande: Commande
  cle_suivi: string
}

export interface CommandeResume {
  reference: string
  statut: Statut
  statut_libelle: string
  est_devis: boolean
  cree_le: string
  nom_client: string
  telephone: string
  etablissement: string | null
  mode_livraison: ModeLivraison
  zone_nom: string | null
  total: number
  montant_paye: number
  nombre_articles: number
  date_promise: string | null
}

export interface PageCommandes {
  elements: CommandeResume[]
  total: number
  page: number
  par_page: number
}

export interface Paiement {
  id: string
  montant: number
  moyen: 'especes' | 'orange_money' | 'moov_money' | 'virement' | 'cheque'
  reference: string | null
  encaisse_le: string
}

export interface CommandeGestion extends Commande {
  id: string
  client_id: string | null
  email: string | null
  note_client: string
  devis_emis_le: string | null
  paiements: Paiement[]
  historique_complet: (Evenement & { visible_client: boolean })[]
  passages_possibles: Statut[]
}

/** Couleur de pastille : ce qui attend l'équipe, ce qui avance, ce qui est terminé. */
export function classeStatut(statut: Statut): string {
  if (statut === 'en_attente' || statut === 'devis_demande') return 'pastille pastille-accent'
  if (statut === 'livree') return 'pastille pastille-succes'
  if (statut === 'annulee' || statut === 'devis_refuse') return 'pastille pastille-danger'
  return 'pastille'
}
