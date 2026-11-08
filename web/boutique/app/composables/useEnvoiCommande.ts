import type { CommandeCreee } from '~/types/commandes'

/**
 * Envoi d'une commande ou d'une demande de devis. La clé de suivi est tirée une fois par
 * l'appareil et réutilisée si l'envoi est répété (réseau coupé) : jamais de doublon.
 */
export function useEnvoiCommande(chemin: '/api/v1/commandes' | '/api/v1/devis') {
  const { appeler } = useApiBoutique()
  const { vider, retenirSuivi } = usePanier()
  const cle = useState<string>(`cle-${chemin}`, () => '')
  const envoi = ref(false)
  const erreur = ref('')

  async function envoyer(corps: Record<string, unknown>) {
    erreur.value = ''
    envoi.value = true
    cle.value ||= crypto.randomUUID()
    try {
      const reponse = await appeler<CommandeCreee>(chemin, {
        method: 'POST', body: { ...corps, cle_suivi: cle.value },
      })
      const { commande, cle_suivi: cleSuivi } = reponse
      retenirSuivi({
        reference: commande.reference, cle: cleSuivi, cree_le: commande.cree_le, est_devis: commande.est_devis,
      })
      vider()
      cle.value = ''
      await navigateTo({ path: `/suivi/${commande.reference}`, query: { cle: cleSuivi, nouvelle: '1' } })
    } catch (e) {
      erreur.value = messageErreur(e)
    } finally {
      envoi.value = false
    }
  }

  return { envoyer, envoi, erreur }
}
