<script setup lang="ts">
import type { EtatOrdre, Ordre, Poste } from '~/types/atelier'

useSeoMeta({ title: 'Atelier', robots: 'noindex' })
const ROLES = ['boutique:atelier', 'boutique:admin']
const ACTIONS: Record<EtatOrdre, string> = {
  en_cours: 'Commencer', controle: 'Au contrôle', termine: 'Terminé', a_faire: 'Remettre à faire', annule: '',
}
const { appeler, telecharger } = useApiBoutique()
const { verifie, autorise, estGestionnaire } = useEquipe(ROLES)
const postes = ref<Poste[]>([])
const ordres = ref<Ordre[]>([])
const poste = ref<string | null>(null)
const erreur = ref('')
const enCours = ref<string | null>(null)
let minuterie: ReturnType<typeof setInterval> | undefined
const piecesEnFile = computed(() => ordres.value.reduce((total, o) => total + o.quantite, 0))

function libelleAction(ordre: Ordre, etat: EtatOrdre) {
  return ordre.etat === 'controle' && etat === 'en_cours' ? 'Retouche' : ACTIONS[etat]
}

async function charger() {
  if (!autorise.value) return
  try {
    const [p, o] = await Promise.all([
      appeler<Poste[]>('/api/v1/atelier/postes'),
      appeler<Ordre[]>('/api/v1/atelier/ordres', { query: { poste: poste.value ?? undefined } }),
    ])
    postes.value = p
    ordres.value = o
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function avancer(ordre: Ordre, etat: EtatOrdre) {
  enCours.value = ordre.id
  try {
    await appeler(`/api/v1/atelier/ordres/${ordre.id}/etat`, { method: 'POST', body: { etat } })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    enCours.value = null
  }
}

async function changerCapacite(code: string, capacite: number) {
  if (!capacite || capacite < 1) return
  try {
    postes.value = await appeler<Poste[]>(`/api/v1/admin/postes/${code}`, {
      method: 'PATCH', body: { capacite_jour: capacite },
    })
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

// Une étiquette par pièce de la file affichée (même poste), à épingler sur le vêtement.
const impression = ref(false)
async function etiquettes() {
  impression.value = true
  try {
    const query = poste.value ? `?poste=${encodeURIComponent(poste.value)}` : ''
    await telecharger(`/api/v1/atelier/etiquettes.pdf${query}`, `etiquettes-${poste.value ?? 'atelier'}.pdf`)
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    impression.value = false
  }
}

watch([verifie, poste], charger)
onMounted(() => { minuterie = setInterval(charger, 60_000) })
onBeforeUnmount(() => clearInterval(minuterie))
</script>

<template>
  <section class="conteneur atelier">
    <AccesEquipe :roles="ROLES">
      <div class="postes">
        <button type="button" class="poste" :class="{ actif: poste === null }" @click="poste = null">
          <strong>Tous les postes</strong>
          <small>{{ piecesEnFile }} pièce{{ piecesEnFile > 1 ? 's' : '' }} en file</small>
        </button>
        <div v-for="p in postes" :key="p.code" class="poste" :class="{ actif: poste === p.code }">
          <button type="button" class="choix" @click="poste = p.code">
            <strong>{{ p.nom }}</strong>
            <small>{{ p.charge }} pièce{{ p.charge > 1 ? 's' : '' }}, {{ p.jours_de_file }} jour{{ p.jours_de_file > 1 ? 's' : '' }} de travail</small>
          </button>
          <label v-if="estGestionnaire" class="capacite">
            Capacité par jour
            <input type="number" min="1" :value="p.capacite_jour" inputmode="numeric" @change="changerCapacite(p.code, Number(($event.target as HTMLInputElement).value))">
          </label>
        </div>
      </div>

      <div v-if="ordres.length" class="outils">
        <button type="button" class="bouton bouton-secondaire" :disabled="impression" @click="etiquettes">
          {{ impression ? 'Préparation…' : `Imprimer les étiquettes (${ordres.length})` }}
        </button>
        <span class="aide">Une par pièce de la file, avec le texte à broder en entier : à épingler sur le vêtement.</span>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <p v-if="verifie && !ordres.length" class="vide">Rien à fabriquer pour le moment.</p>

      <ul class="ordres">
        <li v-for="o in ordres" :key="o.id" class="carte ordre" :class="{ retard: o.en_retard, encours: o.etat !== 'a_faire' }">
          <div class="haut">
            <span class="ref">{{ o.reference }}</span>
            <span class="pastille" :class="{ 'pastille-danger': o.en_retard }">
              {{ o.en_retard ? 'En retard' : o.etat_libelle }}
            </span>
          </div>
          <p class="quoi"><span class="quantite">{{ o.quantite }} ×</span> {{ o.libelle }}</p>
          <p v-if="o.personnalisation" class="texte-a-broder">« {{ o.personnalisation }} »</p>
          <p class="pour">
            Pour {{ o.client }}<template v-if="o.date_promise">, promis le {{ formaterDate(o.date_promise) }}</template>
          </p>
          <div class="actions">
            <button
              v-for="etat in o.passages_possibles" :key="etat" type="button"
              :class="etat === 'a_faire' || (o.etat === 'controle' && etat === 'en_cours') ? 'bouton bouton-secondaire' : 'bouton'"
              :disabled="enCours === o.id" @click="avancer(o, etat)"
            >{{ libelleAction(o, etat) }}</button>
          </div>
        </li>
      </ul>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.outils { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin: 0 0 12px; }
.outils .aide { margin: 0; }
.atelier { padding-top: 20px; }
.postes { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 210px), 1fr)); margin-bottom: 18px; }
.poste {
  display: grid; gap: 6px; padding: 12px 14px; border: 1.5px solid var(--bordure); border-radius: 14px;
  background: var(--surface); text-align: left; font: inherit; color: inherit; cursor: pointer;
}
.poste.actif { border-color: var(--primaire); background: var(--primaire-clair); }
.poste .choix { all: unset; cursor: pointer; display: grid; gap: 2px; }
.poste small { color: var(--texte-doux); }
.capacite { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 0.85rem; color: var(--texte-doux); }
.capacite input { width: 72px; min-height: 36px; padding: 0 8px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; }
.vide { font-size: 1.1rem; color: var(--texte-doux); }
.ordres { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); }
.ordre { padding: 16px; display: grid; gap: 8px; align-content: start; border-left: 6px solid var(--bordure); }
.ordre.encours { border-left-color: var(--primaire); }
.ordre.retard { border-left-color: var(--danger); }
.haut { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.ref { font-weight: 800; font-size: 1.05rem; }
.ordre p { margin: 0; }
.quoi { font-size: 1.15rem; font-weight: 650; line-height: 1.3; }
.quantite { color: var(--primaire); font-size: 1.5rem; font-weight: 800; }
.texte-a-broder {
  padding: 10px 12px; border-radius: 10px; background: var(--accent-clair); color: var(--texte);
  font-size: 1.3rem; font-weight: 700; overflow-wrap: anywhere;
}
.pour { color: var(--texte-doux); }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.actions .bouton { min-height: 54px; flex: 1; font-size: 1.05rem; }
</style>
