<script setup lang="ts">
import type { Commande } from '~/types/commandes'
import type { EtatPaiement, LienDePaiement, PaiementOuvert } from '~/types/paiements'

// Paiement du reste à payer (ou de l'acompte seul, quand il est attendu) par Orange Money ou
// Moov Money, sur la page de l'agrégateur. Au retour (?paiement=retour), le statut est relu
// jusqu'à la réponse de l'opérateur.
// Depuis le suivi ou « Mes commandes », le client peut aussi envoyer un lien de paiement à un
// proche (`partageable`) ; sur la page de ce lien (`espace` « payer »), le proche paie.
const props = withDefaults(defineProps<{
  commande: Pick<Commande, 'reference' | 'montant_paye'> & { statut?: Commande['statut'] }
  base: string
  requete?: Record<string, string>
  cle?: string
  espace?: 'suivi' | 'payer'
  partageable?: boolean
}>(), { requete: undefined, cle: undefined, espace: 'suivi', partageable: true })
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

async function payer(objet: 'acompte' | 'solde' = 'solde') {
  envoi.value = true
  erreur.value = ''
  try {
    const { adresse } = await appeler<PaiementOuvert>(`${props.base}/paiement-mobile`, {
      method: 'POST', query: props.requete, body: { objet },
    })
    // Au retour de la page de paiement, l'onglet retrouve le lien de suivi sans le donner à l'agrégateur.
    if (props.cle) {
      try { sessionStorage.setItem(`bibou:${props.espace}:${props.commande.reference}`, props.cle) } catch { /* navigation privée */ }
    }
    window.location.href = adresse
  } catch (e) {
    erreur.value = messageErreur(e)
    envoi.value = false
  }
}

// Lien pour un proche : chaque demande en crée un nouveau, qui remplace le précédent.
const lien = ref('')
const lienCopie = ref(false)
const peutPartager = ref(false)
async function creerLien() {
  envoi.value = true
  erreur.value = ''
  try {
    const cree = await appeler<LienDePaiement>(`${props.base}/lien-de-paiement`, { method: 'POST', query: props.requete })
    lien.value = `${window.location.origin}/payer/${props.commande.reference}?cle=${cree.cle}`
    peutPartager.value = typeof navigator.share === 'function'
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}
const texteLien = computed(() => `Bonjour, pouvez-vous régler ma commande Bibou ${props.commande.reference} (${formaterFcfa(etat.value?.montant ?? 0)}) par Orange Money ou Moov Money ? Lien sécurisé : ${lien.value}`)
const whatsapp = computed(() => `https://wa.me/?text=${encodeURIComponent(texteLien.value)}`)
async function copierLien() {
  try {
    await navigator.clipboard.writeText(lien.value)
    lienCopie.value = true
  } catch {
    lienCopie.value = false
  }
}
function partager() {
  navigator.share?.({ title: `Commande Bibou ${props.commande.reference}`, text: texteLien.value }).catch(() => {})
}

// Rien à dire (commande annulée sans paiement en ligne, par exemple) : pas de cadre vide.
const visible = computed(() => {
  const e = etat.value
  return !!e && (!!e.dernier || (e.disponible && (e.possible || !!e.raison)))
})

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
  <section v-if="visible" class="paiement" aria-labelledby="titre-paiement">
    <h2 id="titre-paiement">Paiement en ligne</h2>
    <p v-if="message" :class="['alerte', message.classe]" role="status">{{ message.texte }}</p>
    <p v-if="attente" class="aide">Nous attendons la réponse de votre opérateur…</p>
    <button
      v-else-if="etat.dernier?.statut === 'en_cours'" type="button" class="bouton bouton-secondaire"
      @click="attendreConfirmation()"
    >Vérifier le paiement</button>
    <template v-if="etat.possible && etat.acompte">
      <button type="button" class="bouton bouton-large" :disabled="envoi" @click="payer('acompte')">
        {{ envoi ? 'Ouverture du paiement…' : `Payer l'acompte : ${formaterFcfa(etat.acompte)}` }}
      </button>
      <button type="button" class="bouton bouton-secondaire bouton-large" :disabled="envoi" @click="payer('solde')">
        Tout payer : {{ formaterFcfa(etat.montant) }}
      </button>
      <p class="aide">
        Par {{ etat.moyens.join(' ou ') }}, validé sur votre téléphone depuis la page sécurisée de notre
        partenaire de paiement.<template v-if="espace === 'suivi'"> L'acompte peut aussi se régler à la boutique ; le
        reste se paie à la livraison.</template>
      </p>
    </template>
    <template v-else-if="etat.possible">
      <button type="button" class="bouton bouton-large" :disabled="envoi" @click="payer('solde')">
        {{ envoi ? 'Ouverture du paiement…' : `Payer ${formaterFcfa(etat.montant)} par ${etat.moyens.join(' ou ')}` }}
      </button>
      <p class="aide">
        Vous validez le paiement sur votre téléphone, depuis la page sécurisée de notre partenaire de
        paiement.<template v-if="espace === 'suivi'"> Vous pouvez aussi payer à la livraison.</template>
      </p>
    </template>
    <p v-else-if="etat.raison && etat.dernier?.statut !== 'acceptee'" class="aide">{{ etat.raison }}</p>
    <div v-if="partageable && etat.possible" class="proche">
      <button v-if="!lien" type="button" class="bouton bouton-discret" :disabled="envoi" @click="creerLien">
        Faire payer par un proche
      </button>
      <template v-else>
        <p class="aide">
          Envoyez ce lien à la personne qui paie : il montre le montant et vos articles, ni votre numéro ni
          votre adresse. Un nouveau lien remplace le précédent.
        </p>
        <div class="partage">
          <a :href="whatsapp" target="_blank" rel="noopener" class="bouton bouton-secondaire">Envoyer sur WhatsApp</a>
          <button v-if="peutPartager" type="button" class="bouton bouton-secondaire" @click="partager">Partager…</button>
          <button type="button" class="bouton bouton-secondaire" @click="copierLien">{{ lienCopie ? 'Lien copié' : 'Copier le lien' }}</button>
        </div>
      </template>
    </div>
    <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
  </section>
</template>

<style scoped>
.paiement { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--bordure); border-radius: 12px; }
.paiement h2 { margin: 0; font-size: 1.1rem; }
.paiement .alerte { margin: 0; }
.paiement .aide { margin: 0; }
.proche { display: grid; gap: 8px; justify-items: start; padding-top: 8px; border-top: 1px solid var(--bordure); }
.partage { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
