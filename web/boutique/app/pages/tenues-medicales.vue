<script setup lang="ts">
import type { Metier, Rayon } from '~/types/catalogue'

useSeoMeta({ title: 'Tenues médicales', description: 'Blouses, tuniques, pantalons, tenues de bloc, chaussures et accessoires pour tous les métiers de la santé.' })
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const tenues = computed(() => (rayons.value ?? []).filter(r => r.univers === 'tenues'))
</script>

<template>
  <section class="conteneur">
    <EnteteListe titre="Tenues médicales" description="Choisissez par type de vêtement ou par métier. Tout ce qui est marqué Personnalisable se brode à votre nom." />
    <h2>Par type</h2>
    <div class="tuiles">
      <NuxtLink v-for="r in tenues" :key="r.slug" :to="`/rayons/${r.slug}`" class="tuile">
        <ChartePictogramme :type="r.slug" :taille="52" />
        <span><strong>{{ r.nom }}</strong><small>{{ r.nombre_produits }} articles</small></span>
      </NuxtLink>
    </div>
    <h2>Par métier</h2>
    <MetiersTuiles :metiers="metiers ?? []" />
  </section>
</template>

<style scoped>
.tuiles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); }
.tuile { display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--bordure); border-radius: var(--rayon); color: inherit; text-decoration: none; background: var(--surface); }
.tuile:hover { border-color: var(--primaire); }
.tuile strong, .tuile small { display: block; }
.tuile small { color: var(--texte-doux); }
</style>
