<script setup lang="ts">
import type { PageProduits, Rayon } from '~/types/catalogue'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const page = computed(() => Number(route.query.page ?? 1) || 1)

const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const rayon = computed(() => rayons.value?.find(r => r.slug === slug.value))
if (!rayon.value) {
  throw createError({ statusCode: 404, statusMessage: 'Rayon introuvable', fatal: true })
}
const { data: produits } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: computed(() => ({ rayon: slug.value, page: page.value, par_page: 24 })),
})
useSeoMeta({ title: () => rayon.value?.nom ?? 'Rayon', description: () => rayon.value?.description })
</script>

<template>
  <section class="conteneur rayon">
    <NuxtLink to="/" class="retour">← Tous les rayons</NuxtLink>
    <div class="titre">
      <ChartePictogramme :type="slug" :taille="56" />
      <div>
        <h1>{{ rayon?.nom }}</h1>
        <p>{{ rayon?.description }}</p>
      </div>
    </div>
    <GrilleProduits :produits="produits?.elements ?? []" />
    <NavigationPages v-if="produits" :page="produits.page" :total="produits.total" :par-page="produits.par_page" />
  </section>
</template>

<style scoped>
.rayon { padding-top: 24px; }
.retour { display: inline-block; margin-bottom: 16px; text-decoration: none; }
.titre { display: flex; gap: 16px; align-items: flex-start; margin-bottom: 24px; }
.titre p { color: var(--texte-doux); margin: 0; max-width: 640px; }
.titre h1 { margin-bottom: 0.2em; }
</style>
