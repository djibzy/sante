/** Tenues proposées : idées de tenues complètes composées par l'équipe. */
export type Place = 'haut' | 'bas' | 'dessus' | 'chaussures' | 'calot'

export interface PieceProposee {
  piece: Place
  produit_slug: string
  nom: string
  rayon_slug: string
  couleur: string | null
  hex: string | null
  prix: number | null
  personnalisable: boolean
}

export interface TenueProposee {
  id: string
  nom: string
  description: string
  metier: string | null
  pieces: PieceProposee[]
  total: number
}

export interface TenueGestion extends TenueProposee {
  position: number
  est_active: boolean
  incomplete: boolean
}
