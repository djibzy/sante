<script setup lang="ts">
import type { Collecte } from '~/types/prestations'

// Recomptage au retour, devant la structure : chaque article enlevé est recompté ; un écart
// est signalé à la structure dans le SMS du retour.
const props = defineProps<{ collecte: Collecte }>()
const emit = defineEmits<{ fait: [collecte: Collecte]; fermer: [] }>()
const { appeler } = useApiPrestations()
const id = `retour-${props.collecte.reference}`
const quantites = ref<number[]>(props.collecte.lignes.map(l => l.quantite_enlevee))
const recuPar = ref('')
const observations = ref('')
const envoi = ref(false)
const erreur = ref('')
const manquantes = computed(() => props.collecte.lignes
  .reduce((somme, l, i) => somme + Math.max(0, l.quantite_enlevee - (quantites.value[i] ?? 0)), 0))

async function valider() {
  erreur.value = ''
  envoi.value = true
  try {
    const collecte = await appeler<Collecte>(`/api/v1/collectes/${props.collecte.reference}/retour`, {
      method: 'POST',
      body: {
        lignes: props.collecte.lignes.map((l, i) => ({
          article: l.article, precision: l.precision, quantite: quantites.value[i] ?? 0,
        })),
        recu_par: recuPar.value,
        observations: observations.value,
      },
    })
    emit('fait', collecte)
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}
</script>

<template>
  <form class="formulaire-terrain" @submit.prevent="valider">
    <h3>Recompter au retour</h3>
    <table class="recompte">
      <thead><tr><th scope="col">Article</th><th scope="col">Enlevées</th><th scope="col">Rendues</th></tr></thead>
      <tbody>
        <tr v-for="(ligne, i) in collecte.lignes" :key="`${ligne.article}-${ligne.precision}`">
          <th scope="row"><label :for="`${id}-${i}`">{{ ligne.libelle }}</label></th>
          <td>{{ ligne.quantite_enlevee }}</td>
          <td>
            <input :id="`${id}-${i}`" v-model.number="quantites[i]" type="number" inputmode="numeric" min="0" max="10000" required>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="manquantes" class="alerte alerte-erreur">{{ manquantes }} pièce{{ manquantes > 1 ? 's' : '' }} manque{{ manquantes > 1 ? 'nt' : '' }} : la structure en est prévenue, la gestion aussi.</p>
    <div class="champ">
      <label :for="`${id}-recu`">Reçu par (nom, fonction)</label>
      <input :id="`${id}-recu`" v-model="recuPar" required minlength="2" maxlength="120" placeholder="Mariam, lingère">
    </div>
    <div class="champ">
      <label :for="`${id}-obs`">Observations <span class="aide">(facultatif)</span></label>
      <textarea :id="`${id}-obs`" v-model="observations" maxlength="1000" rows="2" />
    </div>
    <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
    <div class="boutons">
      <button type="submit" class="bouton" :disabled="envoi">Valider le retour</button>
      <button type="button" class="bouton bouton-discret" @click="emit('fermer')">Fermer</button>
    </div>
  </form>
</template>

<style scoped>
.recompte { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.recompte th, .recompte td { padding: 6px 4px; border-bottom: 1px solid var(--bordure); text-align: left; }
.recompte td { text-align: right; }
.recompte td input { width: 5em; min-height: 44px; text-align: center; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; }
.recompte thead th:not(:first-child) { text-align: right; }
</style>
