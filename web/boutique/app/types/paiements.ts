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
  raison: string | null
  moyens: string[]
  dernier: DernierPaiement | null
}

export interface PaiementOuvert {
  adresse: string
}
