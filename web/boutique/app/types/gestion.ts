export interface VarianteGestion {
  id: string
  sku: string
  libelle: string
  taille: string | null
  couleur: string | null
  couleur_hex: string | null
  prix: number | null
  position: number
  est_active: boolean
}

export interface ProduitGestion {
  id: string
  slug: string
  nom: string
  resume: string
  description: string
  rayon_slug: string
  rayon_nom: string
  categorie_reglementaire: 'libre' | 'pharmaceutique'
  personnalisable: boolean
  prix_public: number | null
  prix_pro: number | null
  delai_jours: number
  poste_atelier: string | null
  seuil_alerte: number
  metiers: string[]
  genre: string | null
  manches: string | null
  collection: string | null
  matiere: string
  entretien: string
  est_nouveau: boolean
  prix_avant_promo: number | null
  est_actif: boolean
  variantes: VarianteGestion[]
  images: { url: string; texte_alternatif: string }[]
}

export interface RayonGestion {
  id: string
  slug: string
  univers: string
  nom: string
  description: string
  position: number
  est_actif: boolean
}
