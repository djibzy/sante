<script setup lang="ts">
import type { PageProduits, Rayon } from '~/types/catalogue'

useSeoMeta({ title: 'Tenues, imprimés et kits pour la santé' })
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: produits } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: { par_page: 8 },
})
</script>

<template>
  <div>
    <section class="bandeau">
      <div class="conteneur bandeau-contenu">
        <div>
          <h1>Tenues brodées, imprimés et kits pour les soignants</h1>
          <p>
            Fabriqués à Bamako pour les soignants, les structures de santé et les campagnes de
            sensibilisation. Paiement à la livraison.
          </p>
          <FormulaireRecherche />
        </div>
        <img src="/marque/papillon-blanc.png" alt="" width="233" height="260" class="papillon">
      </div>
    </section>
    <svg class="sourire" viewBox="0 0 1000 70" preserveAspectRatio="none" aria-hidden="true">
      <path d="M150 6 Q500 120 850 6 Q500 64 150 6 Z" fill="var(--accent)" />
    </svg>

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
.bandeau { background: var(--primaire); color: #fff; overflow: hidden; }
.bandeau-contenu { display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; gap: 24px; padding-top: 36px; padding-bottom: 28px; }
@media (min-width: 820px) { .bandeau-contenu { grid-template-columns: minmax(0, 1fr) 260px; padding-top: 48px; } }
.bandeau h1 { max-width: 16ch; }
.bandeau p { max-width: 560px; color: #d9d6ff; font-size: 1.05rem; }
.papillon { display: none; width: 233px; height: auto; justify-self: end; }
@media (min-width: 820px) { .papillon { display: block; } }
.sourire { display: block; width: 100%; height: clamp(28px, 6vw, 64px); margin-top: -1px; }
.rayons { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); }
.rayon { display: flex; align-items: center; gap: 12px; padding: 12px; color: inherit; text-decoration: none; }
.rayon:hover { border-color: var(--primaire); }
.rayon strong { display: block; line-height: 1.25; }
.rayon small { color: var(--texte-doux); }
</style>
