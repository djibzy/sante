export type EtatOrdre = 'a_faire' | 'en_cours' | 'controle' | 'termine' | 'annule'

export interface Ordre {
  id: string
  reference: string
  client: string
  poste: string
  libelle: string
  personnalisation: string | null
  quantite: number
  etat: EtatOrdre
  etat_libelle: string
  date_promise: string | null
  en_retard: boolean
  note: string
  passages_possibles: EtatOrdre[]
}

export interface Poste {
  code: string
  nom: string
  capacite_jour: number
  est_actif: boolean
  charge: number
  jours_de_file: number
}

export interface LigneStock {
  produit_id: string
  variante_id: string | null
  produit_slug: string
  libelle: string
  sku: string | null
  niveau: number
  reserve: number
  disponible: number
  seuil_alerte: number
  alerte: boolean
}
