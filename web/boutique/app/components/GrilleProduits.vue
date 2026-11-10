<script setup lang="ts">
import type { ProduitResume } from '~/types/catalogue'

defineProps<{ produits: ProduitResume[] }>()
</script>

<template>
  <div v-if="produits.length" class="grille">
    <CarteProduit v-for="produit in produits" :key="produit.id" :produit="produit" />
  </div>
  <p v-else class="vide">Aucun produit ne correspond.</p>
</template>

<style scoped>
.grille { display: grid; gap: 28px 18px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); }
.vide { color: var(--texte-doux); padding: 2rem 0; }
</style>
