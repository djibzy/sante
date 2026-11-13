<script setup lang="ts">
// Article dessiné dans sa vraie couleur, en attendant ses photos : tunique, blouse, pantalon,
// tenue de bloc, chaussures, gilet, polo, calot, montre. Les tissus wax reçoivent un motif.
const props = defineProps<{
  forme: string
  hex: string
  couleur?: string | null // nom de la couleur : « Wax bleu » donne le motif wax
  brode?: boolean // trace d'une broderie sur la poitrine
  fond?: boolean // fond teinté (tuiles), sinon transparent
  libelle?: string // texte de remplacement ; sans lui, l'illustration est décorative
}>()
const dessinable = computed(() => !!FORMES[props.forme])
const fondTeinte = computed(() => (estClaire(props.hex) ? '#ebe9f5' : melanger(props.hex, '#ffffff', 0.84)))
</script>

<template>
  <svg
    v-if="dessinable" viewBox="0 0 100 125" class="illustration" :role="libelle ? 'img' : undefined"
    :aria-label="libelle" :aria-hidden="libelle ? undefined : 'true'"
  >
    <rect v-if="fond" width="100" height="125" :fill="fondTeinte" />
    <TraceVetement :forme="forme" :hex="hex" :couleur="couleur" :brode="brode" />
  </svg>
</template>

<style scoped>
.illustration { display: block; width: 100%; height: 100%; }
</style>
