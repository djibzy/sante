import type { CommandeCreee } from '~/types/commandes'
import type { CheminEnvoi } from '~/composables/useEnvoiDiffere'

/**
 * Envoi d'une commande ou d'une demande de devis. La clé de suivi est tirée une fois par
 * l'appareil et réutilisée si l'envoi est répété (réseau coupé) : jamais de doublon. Sans
 * réseau, la commande est gardée sur l'appareil et part dès le retour du réseau.
 */
export function useEnvoiCommande(chemin: CheminEnvoi) {
  const { appeler } = useApiBoutique()
  const { vider, retenirSuivi } = usePanier()
  const differe = useEnvoiDiffere()
  const cle = useState<string>(`cle-${chemin}`, () => '')
  const envoi = ref(false)
  const erreur = ref('')
  const gardee = computed(() => differe.enAttente.value?.chemin === chemin)

  async function suivre(reference: string, cleSuivi: string) {
    cle.value = ''
    await navigateTo({ path: `/suivi/${reference}`, query: { cle: cleSuivi, nouvelle: '1' } })
  }

  async function envoyer(corps: Record<string, unknown>) {
    erreur.value = ''
    cle.value ||= crypto.randomUUID()
    const complet = { ...corps, cle_suivi: cle.value }
    const garder = () => differe.garder({ chemin, corps: complet, garde_le: new Date().toISOString() })
    if (!navigator.onLine) {
      garder()
      return
    }
    envoi.value = true
    try {
      const { commande, cle_suivi: cleSuivi } = await appeler<CommandeCreee>(chemin, { method: 'POST', body: complet })
      retenirSuivi({
        reference: commande.reference, cle: cleSuivi, cree_le: commande.cree_le, est_devis: commande.est_devis,
      })
      vider()
      await suivre(commande.reference, cleSuivi)
    } catch (e) {
      if (estCoupure(e) && !navigator.onLine) garder() // réseau perdu pendant l'envoi
      else erreur.value = messageErreur(e)
    } finally {
      envoi.value = false
    }
  }

  function annulerEnvoiGarde() {
    differe.garder(null)
  }

  // Le réseau revient pendant que la page est ouverte : la commande part, on montre son suivi.
  watch(differe.issue, async (issue) => {
    if (issue?.nature === 'envoyee' && cle.value) {
      differe.issue.value = null
      await suivre(issue.reference, issue.cle)
    } else if (issue?.nature === 'refusee') {
      differe.issue.value = null
      erreur.value = issue.message
    }
  })

  return { envoyer, envoi, erreur, gardee, annulerEnvoiGarde }
}
