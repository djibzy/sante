<script setup lang="ts">
import type { PageProduits } from '~/types/catalogue'

useSeoMeta({ title: 'Mes favoris', robots: 'noindex' })
const { slugs } = useFavoris()
const { appeler } = useApiBoutique()
const page = ref<PageProduits | null>(null)
const monte = ref(false)

async function charger() {
  page.value = slugs.value.length
    ? await appeler<PageProduits>('/api/v1/produits', { query: { slug: slugs.value, par_page: 50 } })
    : null
}
onMounted(() => {
  monte.value = true
})
watch([monte, slugs], () => {
  if (monte.value) void charger()
}, { deep: true })
const produits = computed(() => {
  const par = new Map((page.value?.elements ?? []).map(p => [p.slug, p]))
  return slugs.value.map(s => par.get(s)).filter(p => p !== undefined)
})
</script>

<template>
  <section class="conteneur">
    <EnteteListe titre="Mes favoris" description="Gardés sur cet appareil, pour comparer ou commander plus tard." />
    <p v-if="!monte" class="aide">Chargement…</p>
    <div v-else-if="!slugs.length" class="carte vide">
      <p>Touchez le cœur d'une tenue pour la retrouver ici.</p>
      <NuxtLink to="/tenues-medicales" class="bouton">Voir les tenues</NuxtLink>
    </div>
    <GrilleProduits v-else :produits="produits" />
  </section>
</template>

<style scoped>
.vide { padding: 24px; display: grid; justify-items: start; gap: 8px; }
.vide p { margin: 0; }
</style>
