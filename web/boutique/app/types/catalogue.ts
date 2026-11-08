export interface Rayon {
  id: string
  slug: string
  nom: string
  description: string
  nombre_produits: number
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
  image: Image | null
}

export interface Variante {
  id: string
  sku: string
  libelle: string
  taille: string | null
  couleur: string | null
  prix: number | null
}

export interface ProduitDetail extends ProduitResume {
  description: string
  delai_jours: number
  variantes: Variante[]
  images: Image[]
}

export interface PageProduits {
  elements: ProduitResume[]
  total: number
  page: number
  par_page: number
}
