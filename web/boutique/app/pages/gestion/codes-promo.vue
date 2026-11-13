<script setup lang="ts">
// Codes de réduction : créer, suivre les utilisations et les remises accordées, arrêter. Un
// code n'est jamais effacé : les commandes qui l'ont utilisé le gardent.
useSeoMeta({ title: 'Codes promo', robots: 'noindex' })

interface Code {
  id: string
  code: string
  libelle: string
  nature: 'pourcentage' | 'montant'
  valeur: number
  minimum: number
  debut: string
  fin: string | null
  utilisations_max: number | null
  une_fois_par_client: boolean
  est_actif: boolean
  utilisations: number
  remises: number
}

const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const codes = ref<Code[]>([])
const erreur = ref('')
const message = ref('')
const envoi = ref(false)
const BASE = '/api/v1/admin/codes-promo'
const vierge = () => ({
  code: '', libelle: '', nature: 'pourcentage' as Code['nature'], valeur: 10, minimum: 0, debut: '', fin: '',
  utilisations_max: null as number | null, une_fois_par_client: true,
})
const nouveau = reactive(vierge())

async function charger() {
  try {
    codes.value = await appeler<Code[]>(BASE)
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function creer() {
  envoi.value = true
  erreur.value = ''
  message.value = ''
  try {
    const cree = await appeler<Code>(BASE, {
      method: 'POST',
      body: {
        ...nouveau,
        debut: nouveau.debut || null,
        fin: nouveau.fin || null,
        utilisations_max: nouveau.utilisations_max || null,
      },
    })
    message.value = `Code ${cree.code} créé.`
    Object.assign(nouveau, vierge())
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function basculer(code: Code) {
  envoi.value = true
  try {
    await appeler(`${BASE}/${code.id}`, { method: 'PATCH', body: { est_actif: !code.est_actif } })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

const reduction = (c: Pick<Code, 'nature' | 'valeur'>) => (c.nature === 'pourcentage' ? `${c.valeur} %` : formaterFcfa(c.valeur))
function etat(c: Code): { texte: string, classe: string } {
  const aujourdHui = new Date().toISOString().slice(0, 10)
  if (!c.est_actif) return { texte: 'Arrêté', classe: 'pastille pastille-attente' }
  if (c.debut > aujourdHui) return { texte: 'À venir', classe: 'pastille pastille-accent' }
  if (c.fin && c.fin < aujourdHui) return { texte: 'Expiré', classe: 'pastille pastille-attente' }
  if (c.utilisations_max && c.utilisations >= c.utilisations_max) return { texte: 'Épuisé', classe: 'pastille pastille-attente' }
  return { texte: 'En cours', classe: 'pastille pastille-succes' }
}

watch(verifie, () => { if (autorise.value) void charger() }, { immediate: true })
</script>

<template>
  <section class="conteneur codes">
    <AccesEquipe>
      <h1>Codes promo</h1>
      <p class="aide">
        Le client saisit le code au panier : la réduction porte sur les articles, jamais sur la livraison. Une commande
        annulée rend le code.
      </p>

      <form class="carte creation" @submit.prevent="creer">
        <h2>Nouveau code</h2>
        <div class="grille">
          <div class="champ">
            <label for="code">Code</label>
            <input id="code" v-model="nouveau.code" required minlength="3" maxlength="30" pattern="[A-Za-z0-9\-]+" placeholder="BIENVENUE" autocapitalize="characters">
          </div>
          <div class="champ large">
            <label for="libelle">Libellé montré au client</label>
            <input id="libelle" v-model="nouveau.libelle" required minlength="3" maxlength="120" placeholder="Bienvenue chez Bibou : 10 % offerts">
          </div>
          <div class="champ">
            <label for="nature">Réduction</label>
            <select id="nature" v-model="nouveau.nature">
              <option value="pourcentage">Pourcentage</option>
              <option value="montant">Montant en FCFA</option>
            </select>
          </div>
          <div class="champ">
            <label for="valeur">{{ nouveau.nature === 'pourcentage' ? 'Pourcentage (1 à 90)' : 'Montant (FCFA)' }}</label>
            <input id="valeur" v-model.number="nouveau.valeur" type="number" min="1" :max="nouveau.nature === 'pourcentage' ? 90 : 10000000" required>
          </div>
          <div class="champ">
            <label for="minimum">Achat minimal (FCFA)</label>
            <input id="minimum" v-model.number="nouveau.minimum" type="number" min="0" step="500">
          </div>
          <div class="champ">
            <label for="max">Utilisations au plus</label>
            <input id="max" v-model.number="nouveau.utilisations_max" type="number" min="1" placeholder="Sans limite">
          </div>
          <div class="champ">
            <label for="debut">Début</label>
            <input id="debut" v-model="nouveau.debut" type="date">
          </div>
          <div class="champ">
            <label for="fin">Fin (incluse)</label>
            <input id="fin" v-model="nouveau.fin" type="date">
          </div>
        </div>
        <label class="case">
          <input v-model="nouveau.une_fois_par_client" type="checkbox">
          Une seule fois par client (même numéro de téléphone)
        </label>
        <button type="submit" class="bouton" :disabled="envoi">Créer le code</button>
        <p v-if="message" class="alerte alerte-succes" role="status">{{ message }}</p>
      </form>

      <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
      <ul class="liste">
        <li v-for="c in codes" :key="c.id" class="carte code">
          <div class="tete">
            <strong class="valeur-code">{{ c.code }}</strong>
            <span :class="etat(c).classe">{{ etat(c).texte }}</span>
          </div>
          <p>{{ c.libelle }}</p>
          <p class="aide">
            {{ reduction(c) }} sur les articles<template v-if="c.minimum"> dès {{ formaterFcfa(c.minimum) }}</template>
            · du {{ formaterDate(c.debut) }}<template v-if="c.fin"> au {{ formaterDate(c.fin) }}</template>
            <template v-if="c.une_fois_par_client"> · une fois par client</template>
          </p>
          <p>
            Utilisé {{ c.utilisations }} fois<template v-if="c.utilisations_max"> sur {{ c.utilisations_max }}</template>
            · {{ formaterFcfa(c.remises) }} de réductions accordées
          </p>
          <button type="button" class="bouton bouton-secondaire" :disabled="envoi" @click="basculer(c)">
            {{ c.est_actif ? 'Arrêter le code' : 'Réactiver' }}
          </button>
        </li>
      </ul>
      <p v-if="verifie && autorise && !codes.length && !erreur" class="aide">Aucun code pour l'instant.</p>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.codes { padding-top: 20px; }
.creation { padding: 16px; display: grid; gap: 10px; margin: 16px 0; }
.creation h2 { margin: 0; font-size: 1.1rem; }
.grille { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr)); }
.grille .large { grid-column: 1 / -1; }
.creation .bouton { justify-self: start; }
.case { display: flex; align-items: center; gap: 8px; }
.case input { width: 20px; height: 20px; accent-color: var(--primaire); }
.liste { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); }
.code { padding: 14px; display: grid; gap: 6px; align-content: start; }
.code p { margin: 0; }
.code .bouton { justify-self: start; }
.tete { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.valeur-code { font-family: ui-monospace, monospace; font-size: 1.1rem; letter-spacing: 0.04em; }
</style>
