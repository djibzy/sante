<script setup lang="ts">
import type { Commande } from '~/types/commandes'
import type { EtatPaiement, PaiementOuvert } from '~/types/paiements'

// Paiement du reste à payer par Orange Money ou Moov Money, sur la page de l'agrégateur.
// Au retour (?paiement=retour), le statut est relu jusqu'à la réponse de l'opérateur.
const props = defineProps<{
  commande: Commande
  base: string
  requete?: Record<string, string>
  cle?: string
}>()
const emit = defineEmits<{ paye: [] }>()

const route = useRoute()
const { appeler } = useApiBoutique()
const etat = ref<EtatPaiement | null>(null)
const envoi = ref(false)
const attente = ref(false)
const erreur = ref('')
const RELECTURES = 24 // toutes les 5 secondes pendant 2 minutes
let minuterie: ReturnType<typeof setTimeout> | undefined

async function lire(verifier = false) {
  const avant = etat.value?.dernier?.statut
  etat.value = await appeler<EtatPaiement>(`${props.base}/paiement-mobile${verifier ? '/verification' : ''}`, {
    method: verifier ? 'POST' : 'GET', query: props.requete,
  })
  if (verifier && etat.value.dernier?.statut === 'acceptee' && avant !== 'acceptee') emit('paye')
}

async function attendreConfirmation(reste = RELECTURES) {
  attente.value = true
  try {
    await lire(true)
  } catch {
    // réseau coupé : on réessaie au tour suivant
  }
  if (etat.value?.dernier?.statut === 'en_cours' && reste > 1) {
    minuterie = setTimeout(() => attendreConfirmation(reste - 1), 5000)
  } else {
    attente.value = false
  }
}

async function payer() {
  envoi.value = true
  erreur.value = ''
  try {
    const { adresse } = await appeler<PaiementOuvert>(`${props.base}/paiement-mobile`, { method: 'POST', query: props.requete })
    // Au retour de la page de paiement, l'onglet retrouve le lien de suivi sans le donner à l'agrégateur.
    if (props.cle) {
      try { sessionStorage.setItem(`bibou:suivi:${props.commande.reference}`, props.cle) } catch { /* navigation privée */ }
    }
    window.location.href = adresse
  } catch (e) {
    erreur.value = messageErreur(e)
    envoi.value = false
  }
}

const message = computed(() => {
  const dernier = etat.value?.dernier
  if (!dernier) return null
  const montant = formaterFcfa(dernier.montant)
  return {
    en_cours: { classe: 'alerte-info', texte: `Paiement de ${montant} en attente de confirmation. Validez-le sur votre téléphone si ce n'est pas encore fait.` },
    acceptee: { classe: 'alerte-succes', texte: `Paiement de ${montant} reçu. Merci !` },
    refusee: { classe: 'alerte-erreur', texte: `Le paiement de ${montant} n'a pas abouti. Vous pouvez réessayer, ou payer à la livraison.` },
    a_verifier: { classe: 'alerte-info', texte: `Votre paiement de ${montant} est en cours de vérification par notre équipe. Nous vous appelons si besoin.` },
  }[dernier.statut]
})

onMounted(async () => {
  try {
    if (route.query.paiement === 'retour') await attendreConfirmation()
    else await lire()
  } catch {
    etat.value = null // le paiement en ligne reste invisible si l'API ne répond pas
  }
})
onBeforeUnmount(() => clearTimeout(minuterie))
watch(() => [props.commande.statut, props.commande.montant_paye], () => { lire().catch(() => {}) })
</script>

<template>
  <section v-if="etat && (etat.disponible || etat.dernier)" class="paiement" aria-labelledby="titre-paiement">
    <h2 id="titre-paiement">Paiement en ligne</h2>
    <p v-if="message" :class="['alerte', message.classe]" role="status">{{ message.texte }}</p>
    <p v-if="attente" class="aide">Nous attendons la réponse de votre opérateur…</p>
    <button
      v-else-if="etat.dernier?.statut === 'en_cours'" type="button" class="bouton bouton-secondaire"
      @click="attendreConfirmation()"
    >Vérifier le paiement</button>
    <template v-if="etat.possible">
      <button type="button" class="bouton bouton-large" :disabled="envoi" @click="payer">
        {{ envoi ? 'Ouverture du paiement…' : `Payer ${formaterFcfa(etat.montant)} par ${etat.moyens.join(' ou ')}` }}
      </button>
      <p class="aide">
        Vous validez le paiement sur votre téléphone, depuis la page sécurisée de notre partenaire de
        paiement. Vous pouvez aussi payer à la livraison.
      </p>
    </template>
    <p v-else-if="etat.raison && etat.dernier?.statut !== 'acceptee'" class="aide">{{ etat.raison }}</p>
    <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
  </section>
</template>

<style scoped>
.paiement { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--bordure); border-radius: 12px; }
.paiement h2 { margin: 0; font-size: 1.1rem; }
.paiement .alerte { margin: 0; }
.paiement .aide { margin: 0; }
</style>
