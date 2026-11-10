<script setup lang="ts">
import type { Metier } from '~/types/catalogue'

// Tuiles « par métier » : la façon dont les soignants cherchent leur tenue.
defineProps<{ metiers: Metier[] }>()
</script>

<template>
  <div class="metiers">
    <NuxtLink v-for="m in metiers.filter(m => m.nombre_produits)" :key="m.slug" :to="`/metiers/${m.slug}`" class="metier">
      <strong>{{ m.nom }}</strong>
      <small>{{ m.nombre_produits }} articles</small>
    </NuxtLink>
  </div>
</template>

<style scoped>
.metiers { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 150px), 1fr)); }
.metier {
  display: grid; gap: 4px; padding: 18px 16px; border-radius: var(--rayon); text-decoration: none;
  background: var(--primaire-clair); color: var(--primaire-fonce); border-bottom: 4px solid var(--primaire);
}
.metier:hover { background: var(--primaire); color: #fff; }
.metier strong { font-size: 1.02rem; line-height: 1.25; }
.metier small { opacity: 0.8; }
</style>
