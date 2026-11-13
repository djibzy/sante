/** Indicateurs de la boutique sur une période (tableau de bord de l'équipe). */
export interface TableauDeBord {
  du: string
  au: string
  ventes: {
    commandes_recues: number
    commandes_livrees: number
    chiffre_affaires: number
    panier_moyen: number | null
    encaisse: number
    encaisse_par_moyen: Record<string, number>
    encaisse_en_ligne: number
    a_encaisser: number
    annulees: number
  }
  devis: { demandes: number, envoyes: number, acceptes: number, refuses: number, taux_acceptation: number | null }
  delais: { confirmation_heures: number | null, livraison_jours: number | null, a_l_heure: number | null }
  clients: { clients: number, nouveaux: number, avis_publies: number, note_moyenne: number | null, avis_a_relire: number }
  meilleures_ventes: { produit_slug: string | null, libelle: string, quantite: number, montant: number }[]
  alertes: {
    a_traiter: number, acomptes_attendus: number, en_retard: number, stock_bas: number,
    sms_en_echec: number, paiements_a_verifier: number,
  }
  pas: 'jour' | 'semaine'
  serie: { debut: string, chiffre_affaires: number, commandes: number }[]
}
