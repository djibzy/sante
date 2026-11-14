<script setup lang="ts">
import type { Collecte, PartenaireResume } from '~/types/prestations'

// Dépôt chez le partenaire : celui du contrat par défaut ; pesée demandée s'il facture au kilo.
const props = defineProps<{ collecte: Collecte; partenaires: PartenaireResume[] }>()
const emit = defineEmits<{ fait: [collecte: Collecte] }>()
const { appeler } = useApiPrestations()
const id = `depot-${props.collecte.reference}`
const partenaireId = ref(props.collecte.partenaire?.id ?? props.collecte.contrat.partenaire?.id ?? '')
const poids = ref<number | null>(null)
const envoi = ref(false)
const erreur = ref('')
const choisi = computed(() => props.partenaires.find(p => p.id === partenaireId.value))

async function valider() {
  erreur.value = ''
  envoi.value = true
  try {
    emit('fait', await appeler<Collecte>(`/api/v1/collectes/${props.collecte.reference}/depot`, {
      method: 'POST',
      body: { partenaire_id: partenaireId.value || null, poids_kg: poids.value || null },
    }))
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}
</script>

<template>
  <form class="depot" @submit.prevent="valider">
    <div class="champ">
      <label :for="`${id}-partenaire`">Partenaire</label>
      <select :id="`${id}-partenaire`" v-model="partenaireId" required>
        <option value="" disabled>Choisir…</option>
        <option v-for="p in partenaires" :key="p.id" :value="p.id">{{ p.nom }}{{ p.quartier ? ` (${p.quartier})` : '' }}</option>
      </select>
    </div>
    <div v-if="choisi?.pesee_requise" class="champ">
      <label :for="`${id}-poids`">Poids pesé (kg)</label>
      <input :id="`${id}-poids`" v-model.number="poids" type="number" inputmode="decimal" min="0.1" max="9999" step="0.1" required>
    </div>
    <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
    <button type="submit" class="bouton" :disabled="envoi">Déposé chez le partenaire</button>
  </form>
</template>

<style scoped>
.depot { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); align-items: end; }
.depot .bouton { margin-bottom: 1rem; }
</style>
