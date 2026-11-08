<script setup lang="ts">
import type { PageProduits, Rayon } from '~/types/catalogue'

useSeoMeta({ title: 'Accueil' })
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: produits } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: { par_page: 8 },
})
</script>

<template>
  <div>
    <section class="bandeau">
      <div class="conteneur">
        <h1>Tenues, imprimés et kits pour la santé</h1>
        <p>
          Brodés, imprimés et assemblés à Bamako pour les soignants, les structures de santé et
          les campagnes de sensibilisation.
        </p>
        <FormulaireRecherche />
      </div>
    </section>

    <section class="conteneur">
      <h2>Rayons</h2>
      <div class="rayons">
        <NuxtLink v-for="rayon in rayons" :key="rayon.id" :to="`/rayons/${rayon.slug}`" class="carte rayon">
          <ChartePictogramme :type="rayon.slug" :taille="56" />
          <span>
            <strong>{{ rayon.nom }}</strong>
            <small>{{ rayon.nombre_produits }} produits</small>
          </span>
        </NuxtLink>
      </div>

      <h2>Nos produits</h2>
      <GrilleProduits :produits="produits?.elements ?? []" />
    </section>
  </div>
</template>

<style scoped>
.bandeau { background: linear-gradient(135deg, var(--primaire-clair), var(--fond)); padding: 40px 0 36px; }
.bandeau p { max-width: 620px; color: var(--texte-doux); font-size: 1.05rem; }
.rayons { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); }
.rayon { display: flex; align-items: center; gap: 12px; padding: 12px; color: inherit; text-decoration: none; }
.rayon strong { display: block; line-height: 1.25; }
.rayon small { color: var(--texte-doux); }
</style>
