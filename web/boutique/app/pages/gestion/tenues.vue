<script setup lang="ts">
import type { TenueGestion } from '~/types/tenues'

// Idées de tenues proposées aux clients : montrer ou masquer, ranger, retirer. Elles se
// composent dans « Composer ma tenue ».
useSeoMeta({ title: 'Tenues proposées', robots: 'noindex' })
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const tenues = ref<TenueGestion[]>([])
const erreur = ref('')
const envoi = ref(false)
const BASE = '/api/v1/admin/tenues-proposees'

async function charger() {
  try {
    tenues.value = await appeler<TenueGestion[]>(BASE)
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function modifier(tenue: TenueGestion, changements: Partial<Pick<TenueGestion, 'est_active' | 'position'>>) {
  envoi.value = true
  try {
    await appeler(`${BASE}/${tenue.id}`, { method: 'PATCH', body: changements })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

// Monter ou descendre : les positions sont renumérotées dans l'ordre affiché.
async function deplacer(index: number, sens: -1 | 1) {
  const ordre = [...tenues.value]
  const [tenue] = ordre.splice(index, 1)
  ordre.splice(index + sens, 0, tenue!)
  envoi.value = true
  try {
    for (const [position, t] of ordre.entries()) {
      if (t.position !== position) await appeler(`${BASE}/${t.id}`, { method: 'PATCH', body: { position } })
    }
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

const aRetirer = ref<string | null>(null)
async function retirer(tenue: TenueGestion) {
  envoi.value = true
  try {
    await appeler(`${BASE}/${tenue.id}`, { method: 'DELETE' })
    aRetirer.value = null
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

watch(verifie, () => { if (autorise.value) void charger() })
</script>

<template>
  <section class="conteneur tenues-gestion">
    <AccesEquipe>
      <div class="titre">
        <h1>Tenues proposées</h1>
        <NuxtLink to="/composer" class="bouton">Composer une nouvelle tenue</NuxtLink>
      </div>
      <p class="aide">
        Elles apparaissent dans « Idées de tenues », sur la page Explorer et dans le composeur. Pour en créer une,
        composez-la puis touchez « Enregistrer l'idée de tenue ».
      </p>
      <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
      <p v-if="verifie && autorise && !tenues.length && !erreur" class="aide">Aucune tenue proposée pour l'instant.</p>
      <ul class="liste">
        <li v-for="(t, i) in tenues" :key="t.id" class="carte tenue" :class="{ masquee: !t.est_active }">
          <span class="visuel">
            <Mannequin v-bind="habiller(t.pieces).habits" :libelle="t.nom" />
          </span>
          <div class="infos">
            <h2>{{ t.nom }}</h2>
            <p v-if="t.description" class="aide">{{ t.description }}</p>
            <p class="pieces">
              {{ t.pieces.map(p => (p.couleur ? `${p.nom} (${p.couleur})` : p.nom)).join(', ') }}
            </p>
            <p v-if="t.incomplete" class="alerte alerte-info">
              Une pièce n'est plus en vente dans sa couleur : elle n'est plus montrée.
              <template v-if="t.pieces.length < 2">La tenue est masquée aux clients.</template>
            </p>
            <p><strong>{{ formaterFcfa(t.total) }}</strong><span v-if="!t.est_active" class="pastille pastille-attente">Masquée</span></p>
            <div class="actions">
              <button type="button" class="bouton bouton-secondaire" :disabled="envoi" @click="modifier(t, { est_active: !t.est_active })">
                {{ t.est_active ? 'Masquer' : 'Montrer aux clients' }}
              </button>
              <button type="button" class="bouton bouton-discret" :disabled="envoi || i === 0" :aria-label="`Monter ${t.nom}`" @click="deplacer(i, -1)">↑</button>
              <button type="button" class="bouton bouton-discret" :disabled="envoi || i === tenues.length - 1" :aria-label="`Descendre ${t.nom}`" @click="deplacer(i, 1)">↓</button>
              <NuxtLink :to="{ path: '/composer', query: habiller(t.pieces).requete }" class="bouton bouton-discret">Ouvrir dans le composeur</NuxtLink>
              <button v-if="aRetirer !== t.id" type="button" class="bouton bouton-discret" @click="aRetirer = t.id">Retirer</button>
              <span v-else class="confirmation">
                Retirer « {{ t.nom }} » ?
                <button type="button" class="bouton" :disabled="envoi" @click="retirer(t)">Oui, retirer</button>
                <button type="button" class="bouton bouton-secondaire" @click="aRetirer = null">Non</button>
              </span>
            </div>
          </div>
        </li>
      </ul>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.tenues-gestion { padding-top: 20px; }
.titre { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.titre h1 { margin: 0; }
.liste { list-style: none; margin: 16px 0 0; padding: 0; display: grid; gap: 12px; }
.tenue { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 16px; padding: 14px; }
.tenue.masquee .visuel { opacity: 0.5; }
.visuel { height: 220px; border-radius: 10px; background: var(--fond-doux); padding: 6px 0; }
.infos { display: grid; gap: 6px; align-content: start; }
.infos h2 { margin: 0; font-size: 1.1rem; }
.infos p { margin: 0; }
.pieces { font-size: 0.92rem; }
.pastille { margin-left: 8px; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.confirmation { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 6px; font-weight: 650; }
</style>
