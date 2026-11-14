<script setup lang="ts">
import type { ArticleOffre, Collecte, ContratResume } from '~/types/prestations'

// Comptage à l'enlèvement, devant le personnel de la structure. Recompter avant le dépôt
// remplace le comptage précédent (la structure reçoit le SMS corrigé).
const props = defineProps<{
  contrat: ContratResume
  jour: string
  articles: ArticleOffre[]
  collecte?: Collecte | null
}>()
const emit = defineEmits<{ fait: [collecte: Collecte]; fermer: [] }>()
const { appeler } = useApiPrestations()
const id = `enlevement-${props.contrat.reference}`

const depart = props.collecte?.lignes ?? []
const quantites = ref<Record<string, number | null>>(
  Object.fromEntries(depart.map(l => [l.article, l.quantite_enlevee])),
)
const precision = ref(depart.find(l => l.article === 'autre')?.precision ?? '')
const sacs = ref<number | null>(props.collecte?.sacs ?? null)
const remisPar = ref(props.collecte?.remis_par ?? '')
const observations = ref(props.collecte?.observations ?? '')
const envoi = ref(false)
const erreur = ref('')
const total = computed(() => Object.values(quantites.value).reduce<number>((a, b) => a + (b ?? 0), 0))

async function valider() {
  erreur.value = ''
  envoi.value = true
  try {
    const lignes = Object.entries(quantites.value)
      .filter(([, n]) => (n ?? 0) > 0)
      .map(([article, n]) => ({ article, quantite: n, precision: article === 'autre' ? precision.value : '' }))
    const collecte = await appeler<Collecte>('/api/v1/collectes', {
      method: 'POST',
      body: {
        contrat_id: props.contrat.id, jour: props.jour, lignes, sacs: sacs.value,
        remis_par: remisPar.value, observations: observations.value,
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
    <h3>{{ collecte?.statut === 'enlevee' ? 'Recompter le linge' : 'Compter le linge enlevé' }}</h3>
    <p class="aide">Comptez avec la personne qui remet le linge : la structure reçoit le compte par SMS.</p>
    <GrilleArticles v-model="quantites" v-model:precision="precision" :articles="articles" :identifiant="id" />
    <div class="grille-champs">
      <div class="champ">
        <label :for="`${id}-sacs`">Sacs</label>
        <input :id="`${id}-sacs`" v-model.number="sacs" type="number" inputmode="numeric" min="0" max="500">
      </div>
      <div class="champ">
        <label :for="`${id}-remis`">Remis par (nom, fonction)</label>
        <input :id="`${id}-remis`" v-model="remisPar" required minlength="2" maxlength="120" placeholder="Awa, lingère">
      </div>
    </div>
    <div class="champ">
      <label :for="`${id}-obs`">Observations <span class="aide">(taches, accrocs… jamais un nom de patient)</span></label>
      <textarea :id="`${id}-obs`" v-model="observations" maxlength="1000" rows="2" />
    </div>
    <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
    <div class="boutons">
      <button type="submit" class="bouton" :disabled="envoi || !total">Valider {{ total }} pièce{{ total > 1 ? 's' : '' }}</button>
      <button type="button" class="bouton bouton-discret" @click="emit('fermer')">Fermer</button>
    </div>
  </form>
</template>
