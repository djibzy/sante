<script setup lang="ts">
import type { Couleur } from '~/types/catalogue'

// Pastilles de couleur d'un produit ; au-delà de « max », un compteur.
const props = withDefaults(defineProps<{ couleurs: Couleur[]; max?: number }>(), { max: 5 })
const visibles = computed(() => props.couleurs.slice(0, props.max))
const reste = computed(() => props.couleurs.length - visibles.value.length)
</script>

<template>
  <span v-if="couleurs.length > 1 || (couleurs[0] && couleurs[0].hex !== '#ffffff')" class="pastilles" :aria-label="`Couleurs : ${couleurs.map(c => c.nom).join(', ')}`">
    <span v-for="c in visibles" :key="c.nom" class="pastille-couleur" :style="{ background: c.hex ?? '#ccc' }" :title="c.nom" />
    <span v-if="reste > 0" class="reste">+{{ reste }}</span>
  </span>
</template>

<style scoped>
.pastilles { display: inline-flex; align-items: center; gap: 5px; }
.pastille-couleur { width: 14px; height: 14px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.reste { font-size: 0.78rem; color: var(--texte-doux); }
</style>
