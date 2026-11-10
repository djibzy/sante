<script setup lang="ts">
import type { Rayon } from '~/types/catalogue'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const rayon = computed(() => rayons.value?.find(r => r.slug === slug.value))
if (!rayon.value) {
  throw createError({ statusCode: 404, statusMessage: 'Rayon introuvable', fatal: true })
}
const cadre = computed(() => ({ rayon: slug.value }))
useSeoMeta({ title: () => rayon.value?.nom ?? 'Rayon', description: () => rayon.value?.description })
</script>

<template>
  <section class="conteneur">
    <EnteteListe
      :titre="rayon?.nom ?? ''" :description="rayon?.description" :pictogramme="slug"
      :parent="rayon?.univers === 'tenues' ? { nom: 'Tenues médicales', lien: '/tenues-medicales' } : undefined"
    />
    <ListeProduits :key="slug" :cadre="cadre" />
  </section>
</template>
