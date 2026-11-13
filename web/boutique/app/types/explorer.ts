import type { Image } from './catalogue'

/** Découverte visuelle : familles du nuancier et tuiles du mur de couleurs. */
export interface FamilleCouleur {
  code: string
  nom: string
  hex: string
  nombre: number
}

export interface Tuile {
  produit_slug: string
  nom: string
  rayon_slug: string
  genre: 'femme' | 'homme' | 'mixte' | null
  couleur: string
  hex: string
  famille: string
  prix: number | null
  image: Image | null
  distance: number | null // avec une couleur cherchée : 0 (identique) à 100
}

export interface Exploration {
  familles: FamilleCouleur[]
  tuiles: Tuile[]
}
