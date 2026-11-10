<script setup lang="ts">
import type { Rayon } from '~/types/catalogue'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const TITRES: Record<string, { titre: string; description: string }> = {
  tenues: { titre: 'Tenues médicales', description: 'Blouses, tuniques, pantalons, tenues de bloc, chaussures et accessoires.' },
  equipement: { titre: 'Kits et matériel', description: "Kits composés article par article et matériel de mesure. Les articles du domaine pharmaceutique passent par notre pharmacien partenaire." },
  campagnes: { titre: 'Campagnes de sensibilisation', description: 'T-shirts, casquettes, affiches et boîtes à images, conçus avec notre studio.' },
}
const infos = computed(() => TITRES[slug.value])
if (!infos.value) {
  throw createError({ statusCode: 404, statusMessage: 'Page introuvable', fatal: true })
}
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const duMenu = computed(() => (rayons.value ?? []).filter(r => r.univers === slug.value))
const cadre = computed(() => ({ univers: slug.value }))
useSeoMeta({ title: () => infos.value?.titre ?? '' })
</script>

<template>
  <section class="conteneur">
    <EnteteListe :titre="infos?.titre ?? ''" :description="infos?.description" />
    <div class="rayons">
      <NuxtLink v-for="r in duMenu" :key="r.slug" :to="`/rayons/${r.slug}`" class="rayon">
        <ChartePictogramme :type="r.slug" :taille="44" />
        <span>{{ r.nom }}</span>
      </NuxtLink>
    </div>
    <ListeProduits :key="slug" :cadre="cadre" />
  </section>
</template>

<style scoped>
.rayons { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.rayon { display: flex; align-items: center; gap: 10px; padding: 8px 14px 8px 8px; border: 1px solid var(--bordure); border-radius: 999px; color: inherit; text-decoration: none; font-weight: 650; }
.rayon:hover { border-color: var(--primaire); }
</style>
