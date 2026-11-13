import type { LignePanier } from '~/composables/usePanier'

export type Statut =
  | 'devis_demande' | 'devis_envoye' | 'devis_refuse' | 'en_attente' | 'acompte_attendu'
  | 'confirmee' | 'en_preparation' | 'prete' | 'en_livraison' | 'livree' | 'annulee'

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
  a_la_demande: boolean // brodé, imprimé ou personnalisé : compte dans l'acompte
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
  remise: number // code promo, sur les articles
  code_promo: string | null // code accepté
  libelle_promo: string | null
  code_refuse: string | null // pourquoi le code saisi ne s'applique pas
  total: number
  acompte: number // à régler une fois la commande confirmée, non remboursable
  date_estimee: string
  commandable: boolean
}

/** Le même numéro dans les autres commandes, pour l'équipe qui appelle le client. */
export interface ClientDeLaCommande {
  autres_commandes: number
  remises: number
  annulees: number
  depense: number
  client_depuis: string | null
  dernieres: { reference: string, cree_le: string, statut: Statut, statut_libelle: string, total: number }[]
}

/** « Commander à nouveau » : lignes prêtes pour le panier, et ce qui ne revient pas (raison). */
export interface ARecommander {
  lignes: LignePanier[]
  ecartes: string[]
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
  acompte: number // articles faits à la demande, non remboursable
  acompte_restant: number
  acompte_garde: number // annulée par le client : acompte gardé
  rembourse: number // déjà rendu au client (déduit du montant payé)
  code_promo: string | null
  date_promise: string | null
  devis_valable_jusqu_au: string | null
  devis_disponible: boolean
  facture: string | null
  livreur_nom: string | null
  livreur_telephone: string | null
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
  du_au_client: number
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
  moyen: 'especes' | 'orange_money' | 'moov_money' | 'mobile_money' | 'virement' | 'cheque'
  reference: string | null
  encaisse_par: string | null // vide : payé en ligne par le client
  encaisse_le: string
}

export interface Remboursement {
  id: string
  montant: number
  moyen: Paiement['moyen']
  reference: string | null
  motif: string
  rembourse_par: string | null
  rembourse_le: string
}

export interface CommandeGestion extends Commande {
  id: string
  client_id: string | null
  email: string | null
  note_client: string
  tarif_professionnel: boolean
  devis_emis_le: string | null
  paiements: Paiement[]
  remboursements: Remboursement[]
  du_au_client: number // payé au-delà de ce que la boutique garde : à rendre
  historique_complet: (Evenement & { visible_client: boolean })[]
  passages_possibles: Statut[]
}

/** Couleur de pastille : ce qui attend l'équipe, ce qui avance, ce qui est terminé. */
export function classeStatut(statut: Statut): string {
  if (statut === 'en_attente' || statut === 'devis_demande') return 'pastille pastille-accent'
  if (statut === 'acompte_attendu') return 'pastille pastille-attente'
  if (statut === 'livree') return 'pastille pastille-succes'
  if (statut === 'annulee' || statut === 'devis_refuse') return 'pastille pastille-danger'
  return 'pastille'
}

export interface Livreur {
  id: string
  nom: string
  telephone: string
  est_actif: boolean
}

export interface ArretLivraison {
  reference: string
  statut: Statut
  client: string
  telephone: string
  zone_nom: string | null
  adresse: string
  reste_a_payer: number
  nombre_articles: number
  date_promise: string | null
  livreur_id: string | null
  livreur_nom: string | null
}
