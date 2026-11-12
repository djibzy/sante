import type { CommandeCreee } from '~/types/commandes'

/**
 * Commande ou demande de devis préparée sans réseau : gardée sur l'appareil avec sa clé de
 * suivi, puis envoyée dès le retour du réseau. Le serveur reconnaît la clé : un second envoi
 * de la même commande ne crée jamais de doublon, même si le premier était arrivé.
 */
export type CheminEnvoi = '/api/v1/commandes' | '/api/v1/devis'

export interface EnvoiEnAttente {
  chemin: CheminEnvoi
  corps: Record<string, unknown>
  garde_le: string
}

export type IssueEnvoi =
  | { nature: 'envoyee', reference: string, cle: string, est_devis: boolean }
  | { nature: 'refusee', message: string }

const CLE = 'bibou-envoi-en-attente'
const A_REESSAYER = new Set([408, 429, 502, 503, 504])

/** Coupure de réseau ou service momentanément indisponible : l'envoi sera repris. */
export function estCoupure(erreur: unknown): boolean {
  const statut = (erreur as { status?: number, statusCode?: number }).status
    ?? (erreur as { statusCode?: number }).statusCode
  return statut === undefined || A_REESSAYER.has(statut)
}

export function useEnvoiDiffere() {
  const enAttente = useState<EnvoiEnAttente | null>('envoi-en-attente', () => null)
  const issue = useState<IssueEnvoi | null>('envoi-issue', () => null)
  const enCours = useState('envoi-differe-en-cours', () => false)
  const { appeler } = useApiBoutique()
  const { vider, retenirSuivi } = usePanier()

  function garder(envoi: EnvoiEnAttente | null) {
    enAttente.value = envoi
    try {
      if (envoi) localStorage.setItem(CLE, JSON.stringify(envoi))
      else localStorage.removeItem(CLE)
    } catch {
      // stockage indisponible : l'envoi reste gardé le temps de la visite
    }
  }

  function restaurer() {
    try {
      const brut = localStorage.getItem(CLE)
      enAttente.value = brut ? (JSON.parse(brut) as EnvoiEnAttente) : null
    } catch {
      enAttente.value = null
    }
  }

  /** Envoie la commande gardée. Sans réseau, elle reste gardée pour le prochain essai. */
  async function tenter() {
    const envoi = enAttente.value
    if (!envoi || enCours.value) return
    enCours.value = true
    try {
      const { commande, cle_suivi: cle } = await appeler<CommandeCreee>(envoi.chemin, { method: 'POST', body: envoi.corps })
      retenirSuivi({ reference: commande.reference, cle, cree_le: commande.cree_le, est_devis: commande.est_devis })
      vider()
      garder(null)
      useState<string>(`cle-${envoi.chemin}`).value = '' // la prochaine commande aura sa propre clé
      issue.value = { nature: 'envoyee', reference: commande.reference, cle, est_devis: commande.est_devis }
    } catch (e) {
      if (!estCoupure(e)) {
        garder(null) // refus du serveur (article indisponible…) : le panier reste, à corriger
        issue.value = { nature: 'refusee', message: messageErreur(e) }
      }
    } finally {
      enCours.value = false
    }
  }

  return { enAttente, issue, enCours, garder, restaurer, tenter }
}
