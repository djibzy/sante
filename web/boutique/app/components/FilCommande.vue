<script setup lang="ts">
import type { EntreeFil, Fil } from '~/types/commandes'

// Le fil d'une commande ou d'un devis : messages du client et de la boutique, propositions à
// accepter, étapes et paiements, dans l'ordre où ils sont arrivés. Le même composant sert au
// client (lien de suivi ou compte) et à l'équipe (gestion). Rien ne se modifie : l'équipe peut
// seulement retirer un message qui n'a rien à faire ici, et ce retrait reste affiché.
const props = defineProps<{
  base: string // /api/v1/suivi/BB-1001, /api/v1/mes-commandes/BB-1001 ou /api/v1/admin/commandes/BB-1001
  requete?: Record<string, string> // clé du lien de suivi
  equipe?: boolean
}>()
const emit = defineEmits<{ change: [fil: Fil] }>()
const { appeler } = useApiBoutique()
const RAFRAICHIR_MS = 25_000

const fil = ref<Fil | null>(null)
const erreur = ref('')
const texte = ref('')
const proposition = ref(false)
const image = ref<File | null>(null)
const champImage = ref<HTMLInputElement | null>(null)
const envoi = ref(false)
const reponse = ref<string | null>(null) // proposition en cours de réponse
const aRetirer = ref<string | null>(null)
const motif = ref('')
const racine = ref<HTMLElement | null>(null)
const aLEcran = ref(false)
const moi = computed(() => (props.equipe ? 'equipe' : 'client'))

async function charger() {
  try {
    fil.value = await appeler<Fil>(`${props.base}/fil`, { query: props.requete })
    emit('change', fil.value)
    await marquerLu()
  } catch (e) {
    // Au rafraîchissement, une coupure de réseau ne vide pas ce qui est affiché.
    if (!fil.value) erreur.value = messageErreur(e)
  }
}

/** Les messages de l'autre partie sont lus quand le fil est vraiment sous les yeux. */
async function marquerLu() {
  if (!aLEcran.value || document.hidden || !fil.value?.a_lire) return
  try {
    await appeler(`${props.base}/messages/lecture`, { method: 'POST', query: props.requete })
    fil.value.a_lire = 0
    emit('change', fil.value)
  } catch {
    // au prochain passage
  }
}

function choisirImage(evenement: Event) {
  image.value = (evenement.target as HTMLInputElement).files?.[0] ?? null
}

async function envoyer() {
  erreur.value = ''
  envoi.value = true
  try {
    const corps = new FormData()
    corps.append('texte', texte.value)
    if (props.equipe && proposition.value) corps.append('proposition', 'true')
    if (image.value) corps.append('image', await reduireImage(image.value), 'image.jpg')
    await appeler(`${props.base}/messages`, { method: 'POST', body: corps, query: props.requete })
    texte.value = ''
    proposition.value = false
    image.value = null
    if (champImage.value) champImage.value.value = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function agir(chemin: string, corps?: Record<string, unknown>) {
  erreur.value = ''
  try {
    await appeler(`${props.base}/${chemin}`, { method: 'POST', body: corps, query: props.requete })
    aRetirer.value = null
    motif.value = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function repondre(entree: EntreeFil, accepte: boolean) {
  reponse.value = entree.id
  await agir(`propositions/${entree.id}/reponse`, { accepte })
  reponse.value = null
}

function auteur(entree: EntreeFil): string {
  if (entree.auteur === moi.value) return props.equipe ? (entree.nom_auteur || 'L\'équipe') : 'Vous'
  return entree.auteur === 'equipe' ? 'Bibou' : 'Le client'
}

const peutRetirer = (entree: EntreeFil) => props.equipe && !entree.retire && entree.etat !== 'acceptee'

let minuteur: ReturnType<typeof setInterval> | undefined
let observateur: IntersectionObserver | undefined
onMounted(async () => {
  await charger()
  minuteur = setInterval(() => {
    if (!document.hidden && !envoi.value) void charger()
  }, RAFRAICHIR_MS)
  if (racine.value && 'IntersectionObserver' in window) {
    observateur = new IntersectionObserver(([vue]) => {
      aLEcran.value = !!vue?.isIntersecting
      void marquerLu()
    }, { threshold: 0.2 })
    observateur.observe(racine.value)
  } else {
    aLEcran.value = true
    void marquerLu()
  }
})
onBeforeUnmount(() => {
  clearInterval(minuteur)
  observateur?.disconnect()
})
defineExpose({ charger })
</script>

<template>
  <section ref="racine" class="fil" aria-labelledby="titre-fil">
    <header class="entete-fil">
      <h2 id="titre-fil">{{ equipe ? 'Fil de la commande' : 'Suivi et messages' }}</h2>
      <span v-if="fil?.a_lire" class="pastille pastille-accent">{{ fil.a_lire }} nouveau{{ fil.a_lire > 1 ? 'x' : '' }}</span>
    </header>
    <p v-if="!fil && !erreur" class="aide">Chargement du fil…</p>
    <ol v-if="fil" class="entrees">
      <li v-for="(entree, i) in fil.entrees" :key="entree.id ?? `${entree.type}-${entree.quand}-${i}`" :class="['entree', entree.type, { mien: entree.auteur === moi, interne: entree.interne }]">
        <template v-if="entree.type === 'etape' || entree.type === 'paiement' || entree.type === 'remboursement'">
          <p class="jalon">
            <strong>{{ entree.libelle }}</strong>
            <template v-if="entree.montant !== null"> : {{ formaterFcfa(entree.montant) }}</template>
            <time :datetime="entree.quand">{{ formaterDateHeure(entree.quand) }}</time>
          </p>
          <p v-if="entree.note" class="note">{{ entree.note }}<em v-if="entree.interne"> (note interne)</em></p>
        </template>

        <div v-else class="bulle" :class="{ proposition: entree.type === 'proposition' }">
          <p class="qui">
            <strong>{{ entree.type === 'proposition' ? `Proposition de ${equipe ? auteur(entree) : 'Bibou'}` : auteur(entree) }}</strong>
            <time :datetime="entree.quand">{{ formaterDateHeure(entree.quand) }}</time>
          </p>
          <p v-if="entree.retire" class="retire">
            Message retiré par la boutique<template v-if="entree.motif_retrait"> : {{ entree.motif_retrait }}</template>
          </p>
          <template v-else>
            <p v-if="entree.texte" class="texte">{{ entree.texte }}</p>
            <ImageDuFil
              v-if="entree.image" :chemin="`${base}/messages/${entree.id}/image`" :requete="requete"
              :description="`Image jointe par ${auteur(entree).toLowerCase()}`"
            />
          </template>

          <template v-if="entree.type === 'proposition' && !entree.retire">
            <div v-if="entree.etat === 'en_attente' && !equipe && fil.ouvert" class="boutons">
              <button type="button" class="bouton" :disabled="reponse !== null" @click="repondre(entree, true)">J'accepte</button>
              <button type="button" class="bouton bouton-secondaire" :disabled="reponse !== null" @click="repondre(entree, false)">Je refuse</button>
            </div>
            <p v-else class="etat" :class="entree.etat ?? ''">
              {{ equipe && entree.etat === 'en_attente' ? 'En attente de la réponse du client' : entree.libelle_etat }}
              <template v-if="entree.repondue_le && entree.etat !== 'en_attente'"> le {{ formaterDateHeure(entree.repondue_le) }}</template>
            </p>
            <p v-if="entree.etat === 'en_attente' && !equipe" class="aide">Votre réponse est datée et fait foi pour la suite de la commande.</p>
          </template>

          <p v-if="entree.auteur === moi && entree.lu_le && !entree.retire" class="vu">Vu le {{ formaterDateHeure(entree.lu_le) }}</p>
          <div v-if="equipe" class="actions-equipe">
            <button v-if="entree.etat === 'en_attente'" type="button" class="lien" @click="agir(`propositions/${entree.id}/annulation`)">Annuler la proposition</button>
            <button v-if="peutRetirer(entree) && aRetirer !== entree.id" type="button" class="lien" @click="aRetirer = entree.id; motif = ''">Retirer</button>
          </div>
          <form v-if="aRetirer === entree.id" class="retrait" @submit.prevent="agir(`messages/${entree.id}/retrait`, { motif })">
            <div class="champ">
              <label :for="`motif-${entree.id}`">Pourquoi retirer ce message ?</label>
              <input :id="`motif-${entree.id}`" v-model="motif" required minlength="3" maxlength="200" placeholder="Information de santé, envoyé par erreur…">
            </div>
            <p class="aide">Le texte et l'image disparaissent ; le retrait et son motif restent dans le fil.</p>
            <div class="boutons">
              <button type="submit" class="bouton">Retirer ce message</button>
              <button type="button" class="bouton bouton-discret" @click="aRetirer = null">Garder</button>
            </div>
          </form>
        </div>
      </li>
    </ol>

    <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
    <form v-if="fil?.ouvert" class="ecrire" @submit.prevent="envoyer">
      <div class="champ">
        <label for="message-fil">{{ equipe ? 'Écrire au client' : 'Écrire à la boutique' }}</label>
        <textarea id="message-fil" v-model="texte" rows="3" maxlength="2000" :placeholder="equipe ? 'Votre réponse, ou la proposition à faire accepter…' : 'Une question, une précision sur votre commande…'" />
      </div>
      <div class="champ">
        <label for="image-fil">Joindre une image <span class="aide">(logo, modèle ; facultatif)</span></label>
        <input id="image-fil" ref="champImage" type="file" accept="image/jpeg,image/png,image/webp" @change="choisirImage">
      </div>
      <label v-if="equipe" class="case">
        <input v-model="proposition" type="checkbox">
        <span>À faire accepter par le client <span class="aide">(texte à broder, couleur de remplacement, date… son accord est daté et fait foi)</span></span>
      </label>
      <p class="aide rappel">
        Ce fil sert à la commande : {{ equipe ? 'aucune information de santé ici. Un message qui en contient se retire.' : 'n\'y écrivez rien sur la santé d\'un patient, ni sur la vôtre.' }}
      </p>
      <button type="submit" class="bouton" :disabled="envoi || (!texte.trim() && !image)">
        {{ envoi ? 'Envoi…' : proposition ? 'Proposer au client' : 'Envoyer' }}
      </button>
    </form>
    <p v-else-if="fil" class="aide">Cette commande est archivée : son fil est fermé.</p>
  </section>
</template>

<style scoped>
.fil { display: grid; gap: 12px; }
.entete-fil { display: flex; align-items: center; gap: 10px; }
.entete-fil h2 { margin: 0; font-size: 1.1rem; }
.entrees { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.entree { display: grid; }
.jalon { margin: 0; font-size: 0.92rem; color: var(--texte-doux); display: flex; flex-wrap: wrap; gap: 2px 8px; align-items: baseline; padding-left: 18px; position: relative; }
.jalon::before { content: ''; position: absolute; left: 2px; top: 0.5em; width: 8px; height: 8px; border-radius: 50%; background: var(--primaire); }
.paiement .jalon::before, .remboursement .jalon::before { background: var(--succes); }
.jalon strong { color: var(--texte); }
.interne .jalon strong { color: var(--texte-doux); }
.note { margin: 2px 0 0 18px; font-size: 0.92rem; }
time { color: var(--texte-doux); font-size: 0.85rem; }
.bulle { max-width: min(100%, 560px); padding: 10px 14px; border-radius: 14px; background: var(--fond-doux); display: grid; gap: 6px; justify-self: start; }
.mien .bulle { justify-self: end; background: var(--primaire-clair); }
.bulle.proposition { background: var(--surface); border: 2px solid var(--primaire); max-width: 100%; justify-self: stretch; }
.bulle p { margin: 0; }
.qui { display: flex; flex-wrap: wrap; gap: 2px 8px; align-items: baseline; font-size: 0.92rem; }
.texte { white-space: pre-wrap; overflow-wrap: anywhere; }
.retire { font-style: italic; color: var(--texte-doux); }
.etat { font-weight: 700; }
.etat.acceptee { color: var(--succes); }
.etat.refusee, .etat.annulee { color: var(--texte-doux); }
.vu { font-size: 0.82rem; color: var(--texte-doux); text-align: right; }
.boutons { display: flex; flex-wrap: wrap; gap: 8px; }
.actions-equipe { display: flex; gap: 14px; justify-content: flex-end; }
.lien { background: none; border: 0; padding: 4px 0; font: inherit; font-size: 0.88rem; color: var(--texte-doux); text-decoration: underline; cursor: pointer; min-height: 32px; }
.lien:hover { color: var(--danger); }
.retrait { border-top: 1px dashed var(--bordure); padding-top: 8px; display: grid; gap: 4px; }
.ecrire { border-top: 1px solid var(--bordure); padding-top: 12px; display: grid; gap: 2px; justify-items: start; }
.ecrire .champ { width: 100%; }
.case { display: flex; gap: 8px; align-items: flex-start; font-weight: 600; margin-bottom: 8px; }
.case input { width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px; }
.rappel { margin: 0 0 8px; }
</style>
