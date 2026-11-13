/** Paiement mobile en ligne (Orange Money, Moov Money), vu par le client. */
export interface DernierPaiement {
  statut: 'en_cours' | 'acceptee' | 'refusee' | 'a_verifier'
  montant: number
  cree_le: string
}

export interface EtatPaiement {
  disponible: boolean
  possible: boolean
  montant: number
  acompte: number | null // en attente de l'acompte : il peut se payer seul
  raison: string | null
  moyens: string[]
  dernier: DernierPaiement | null
}

/** Lien à envoyer à un proche : il voit le montant dû et paie, rien d'autre. */
export interface LienDePaiement {
  adresse: string
  cle: string
}

export interface CommandeAPayer {
  reference: string
  statut_libelle: string
  pour: string // prénom et initiale du nom
  articles: { libelle: string, quantite: number }[]
  total: number
  montant_paye: number
  reste_a_payer: number
  acompte_restant: number
}

export interface PaiementOuvert {
  adresse: string
}
