<script setup lang="ts">
defineProps<{ montant: number | null; surDemande?: string }>()
</script>

<template>
  <span class="prix">
    <template v-if="montant !== null">{{ formaterFcfa(montant) }}</template>
    <template v-else>{{ surDemande ?? 'Sur demande' }}</template>
  </span>
</template>

<style scoped>
.prix { font-weight: 700; color: var(--texte); white-space: nowrap; }
</style>
