<script setup lang="ts">
import type { PageProduits } from '~/types/catalogue'

const route = useRoute()
const q = computed(() => String(route.query.q ?? ''))
const page = computed(() => Number(route.query.page ?? 1) || 1)
const { data: resultats } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: computed(() => ({ q: q.value, page: page.value, par_page: 24 })),
})
useSeoMeta({ title: () => `Recherche : ${q.value}` })
</script>

<template>
  <section class="conteneur recherche">
    <h1>Recherche</h1>
    <FormulaireRecherche :key="q" :valeur="q" />
    <p class="nombre">{{ resultats?.total ?? 0 }} produit(s) pour « {{ q }} »</p>
    <GrilleProduits :produits="resultats?.elements ?? []" />
    <NavigationPages v-if="resultats" :page="resultats.page" :total="resultats.total" :par-page="resultats.par_page" />
  </section>
</template>

<style scoped>
.recherche { padding-top: 24px; }
.nombre { color: var(--texte-doux); margin: 16px 0; }
</style>
