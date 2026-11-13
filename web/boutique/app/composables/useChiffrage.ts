import type { Chiffrage, Zone } from '~/types/commandes'

/** Prix du panier recalculés par le serveur à chaque changement (panier ou livraison). */
export function useChiffrage() {
  const { demande, livraison, codePromo } = usePanier()
  const { appeler } = useApiBoutique()
  const chiffrage = ref<Chiffrage | null>(null)
  const zones = ref<Zone[]>([])
  const enCours = ref(false)
  const erreur = ref('')
  let minuterie: ReturnType<typeof setTimeout> | undefined

  async function recalculer() {
    if (!demande.value.length) {
      chiffrage.value = null
      return
    }
    enCours.value = true
    try {
      chiffrage.value = await appeler<Chiffrage>('/api/v1/panier/chiffrage', {
        method: 'POST',
        body: {
          lignes: demande.value,
          livraison: { mode: livraison.value.mode, zone_id: livraison.value.zone_id },
          code_promo: codePromo.value || null,
        },
      })
      erreur.value = ''
    } catch (e) {
      erreur.value = messageErreur(e)
    } finally {
      enCours.value = false
    }
  }

  onMounted(async () => {
    try {
      zones.value = await appeler<Zone[]>('/api/v1/zones-livraison')
    } catch {
      zones.value = []
    }
    watch([demande, () => livraison.value.mode, () => livraison.value.zone_id, codePromo], () => {
      clearTimeout(minuterie)
      minuterie = setTimeout(recalculer, 250)
    }, { immediate: true, deep: true })
  })

  return { chiffrage, zones, enCours, erreur, recalculer }
}
