export type Univers = 'tenues' | 'equipement' | 'campagnes'

export interface Rayon {
  id: string
  slug: string
  nom: string
  description: string
  univers: Univers
  nombre_produits: number
}

export interface Metier {
  slug: string
  nom: string
  nombre_produits: number
}

export interface Couleur {
  nom: string
  hex: string | null
}

export interface Facette {
  valeur: string
  libelle: string
  nombre: number
  hex?: string | null
}

export interface Facettes {
  metiers: Facette[]
  genres: Facette[]
  couleurs: Facette[]
  tailles: Facette[]
  collections: Facette[]
}

export interface Image {
  url: string
  texte_alternatif: string
}

export interface ProduitResume {
  id: string
  slug: string
  nom: string
  resume: string
  rayon_slug: string
  rayon_nom: string
  categorie_reglementaire: 'libre' | 'pharmaceutique'
  vendable_en_ligne: boolean
  personnalisable: boolean
  prix_public: number | null
  prix_pro: number | null
  prix_avant_promo: number | null
  image: Image | null
  genre: 'femme' | 'homme' | 'mixte' | null
  metiers: string[]
  collection: string | null
  est_nouveau: boolean
  couleurs: Couleur[]
  tailles: string[]
  delai_jours: number
  fabrique_sur_commande: boolean
  note_moyenne: number | null
  nombre_avis: number
}

export interface Variante {
  id: string
  sku: string
  libelle: string
  taille: string | null
  couleur: string | null
  couleur_hex: string | null
  prix: number | null
}

export interface ProduitDetail extends ProduitResume {
  acompte_pourcent: number | null // fait à la demande : acompte non remboursable, en %
  acompte_toujours: boolean // sinon, seulement s'il est personnalisé
  description: string
  manches: 'courtes' | 'longues' | null
  matiere: string
  entretien: string
  variantes: Variante[]
  images: Image[]
}

export interface PageProduits {
  elements: ProduitResume[]
  total: number
  page: number
  par_page: number
  facettes: Facettes
}
