/** Avis clients vérifiés : seuls les clients qui ont reçu un produit peuvent le noter. */
export type StatutAvis = 'en_attente' | 'publie' | 'refuse'

export interface AvisClient {
  note: number
  texte: string
  statut: StatutAvis
  motif_refus: string | null
  reponse: string | null
}

export interface ProduitAEvaluer {
  produit_id: string
  slug: string
  nom: string
  image: { url: string, texte_alternatif: string } | null
  avis: AvisClient | null
}

export interface AvisCommande {
  possible: boolean
  raison: string | null
  produits: ProduitAEvaluer[]
}

export interface AvisPublic {
  id: string
  auteur: string
  note: number
  texte: string
  reponse: string | null
  date: string
  achat_verifie: boolean
}

export interface PageAvis {
  moyenne: number | null
  nombre: number
  repartition: Record<string, number>
  elements: AvisPublic[]
  page: number
  par_page: number
}

export interface AvisGestion {
  id: string
  produit_id: string
  produit_nom: string
  produit_slug: string
  commande_reference: string
  auteur: string
  note: number
  texte: string
  statut: StatutAvis
  motif_refus: string | null
  reponse: string | null
  cree_le: string
  modere_le: string | null
}

export interface PageAvisGestion {
  elements: AvisGestion[]
  total: number
  page: number
  par_page: number
}

/** « 4,6 » : une décimale, virgule française. */
export function formaterNote(note: number): string {
  return note.toLocaleString('fr-FR', { maximumFractionDigits: 1 })
}
