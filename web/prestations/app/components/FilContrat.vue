<script setup lang="ts">
import type { EntreeFil, Fil } from '~/types/prestations'

// Le fil d'un contrat : messages entre la structure et l'équipe, gardés avec leur date. Le même
// composant sert à la structure (lien de suivi) et à l'équipe (gestion). Rien ne se modifie :
// l'équipe peut seulement retirer un message qui n'a rien à faire ici, et ce retrait reste affiché.
const props = defineProps<{
  base: string // /api/v1/contrat/CT-101 ou /api/v1/admin/contrats/CT-101
  requete?: Record<string, string> // clé du lien de suivi
  equipe?: boolean
}>()
const emit = defineEmits<{ change: [fil: Fil] }>()
const { appeler } = useApiPrestations()
const RAFRAICHIR_MS = 25_000

const fil = ref<Fil | null>(null)
const erreur = ref('')
const texte = ref('')
const envoi = ref(false)
const aRetirer = ref<string | null>(null)
const motif = ref('')
const racine = ref<HTMLElement | null>(null)
const aLEcran = ref(false)
const moi = computed(() => (props.equipe ? 'equipe' : 'structure'))

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

async function envoyer() {
  erreur.value = ''
  envoi.value = true
  try {
    await appeler(`${props.base}/messages`, { method: 'POST', body: { texte: texte.value }, query: props.requete })
    texte.value = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function retirer(entree: EntreeFil) {
  erreur.value = ''
  try {
    await appeler(`${props.base}/messages/${entree.id}/retrait`, { method: 'POST', body: { motif: motif.value } })
    aRetirer.value = null
    motif.value = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function auteur(entree: EntreeFil): string {
  if (entree.auteur === moi.value) return props.equipe ? (entree.nom_auteur || 'L\'équipe') : 'Vous'
  return entree.auteur === 'equipe' ? 'Yasal Santé' : (fil.value?.structure ?? 'La structure')
}

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
      <h2 id="titre-fil">{{ equipe ? 'Messages de la structure' : 'Messages avec Yasal Santé' }}</h2>
      <span v-if="fil?.a_lire" class="pastille pastille-accent">{{ fil.a_lire }} nouveau{{ fil.a_lire > 1 ? 'x' : '' }}</span>
    </header>
    <p v-if="!fil && !erreur" class="aide">Chargement des messages…</p>
    <p v-if="fil && !fil.entrees.length" class="aide">Aucun message pour l'instant.</p>

    <ol v-if="fil" class="entrees">
      <li v-for="entree in fil.entrees" :key="entree.id" :class="['entree', { mien: entree.auteur === moi }]">
        <div class="bulle">
          <p class="qui">
            <strong>{{ auteur(entree) }}</strong>
            <time :datetime="entree.quand">{{ formaterDateHeure(entree.quand) }}</time>
          </p>
          <p v-if="entree.retire" class="retire">
            Message retiré par l'équipe<template v-if="entree.motif_retrait"> : {{ entree.motif_retrait }}</template>
          </p>
          <p v-else class="texte">{{ entree.texte }}</p>
          <p v-if="entree.auteur === moi && entree.lu_le && !entree.retire" class="vu">Vu le {{ formaterDateHeure(entree.lu_le) }}</p>
          <div v-if="equipe && !entree.retire && aRetirer !== entree.id" class="actions-equipe">
            <button type="button" class="lien" @click="aRetirer = entree.id; motif = ''">Retirer</button>
          </div>
          <form v-if="aRetirer === entree.id" class="retrait" @submit.prevent="retirer(entree)">
            <div class="champ">
              <label :for="`motif-${entree.id}`">Pourquoi retirer ce message ?</label>
              <input :id="`motif-${entree.id}`" v-model="motif" required minlength="3" maxlength="200" placeholder="Information de santé, envoyé par erreur…">
            </div>
            <p class="aide">Le texte disparaît ; le retrait et son motif restent dans le fil.</p>
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
        <label for="message-fil">{{ equipe ? 'Écrire à la structure' : 'Écrire à Yasal Santé' }}</label>
        <textarea id="message-fil" v-model="texte" rows="3" maxlength="2000" :placeholder="equipe ? 'Votre message…' : 'Une question sur une collecte, un retour, un relevé…'" />
      </div>
      <p class="aide rappel">
        Ce fil sert au service de linge : {{ equipe ? 'aucune information de santé ici. Un message qui en contient se retire.' : 'n\'y écrivez rien sur la santé d\'un patient.' }}
      </p>
      <button type="submit" class="bouton" :disabled="envoi || !texte.trim()">{{ envoi ? 'Envoi…' : 'Envoyer' }}</button>
    </form>
    <p v-else-if="fil" class="aide">Ce contrat est terminé : son fil est fermé.</p>
  </section>
</template>

<style scoped>
.fil { display: grid; gap: 12px; }
.entete-fil { display: flex; align-items: center; gap: 10px; }
.entete-fil h2 { margin: 0; font-size: 1.1rem; }
.entrees { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.entree { display: grid; }
time { color: var(--texte-doux); font-size: 0.85rem; }
.bulle { max-width: min(100%, 560px); padding: 10px 14px; border-radius: 14px; background: var(--fond-doux); display: grid; gap: 6px; justify-self: start; }
.mien .bulle { justify-self: end; background: var(--primaire-clair); }
.bulle p { margin: 0; }
.qui { display: flex; flex-wrap: wrap; gap: 2px 8px; align-items: baseline; font-size: 0.92rem; }
.texte { white-space: pre-wrap; overflow-wrap: anywhere; }
.retire { font-style: italic; color: var(--texte-doux); }
.vu { font-size: 0.82rem; color: var(--texte-doux); text-align: right; }
.boutons { display: flex; flex-wrap: wrap; gap: 8px; }
.actions-equipe { display: flex; justify-content: flex-end; }
.lien { background: none; border: 0; padding: 4px 0; font: inherit; font-size: 0.88rem; color: var(--texte-doux); text-decoration: underline; cursor: pointer; min-height: 32px; }
.lien:hover { color: var(--danger); }
.retrait { border-top: 1px dashed var(--bordure); padding-top: 8px; display: grid; gap: 4px; }
.ecrire { border-top: 1px solid var(--bordure); padding-top: 12px; display: grid; gap: 2px; justify-items: start; }
.ecrire .champ { width: 100%; }
.rappel { margin: 0 0 8px; }
</style>
