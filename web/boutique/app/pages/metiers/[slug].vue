<script setup lang="ts">
import type { Metier } from '~/types/catalogue'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const metier = computed(() => metiers.value?.find(m => m.slug === slug.value))
if (!metier.value) {
  throw createError({ statusCode: 404, statusMessage: 'Métier introuvable', fatal: true })
}
const cadre = computed(() => ({ metier: slug.value }))
const titre = computed(() => `Tenues et accessoires : ${metier.value?.nom.toLowerCase()}`)
useSeoMeta({ title: titre })
</script>

<template>
  <section class="conteneur">
    <EnteteListe
      :titre="metier?.nom ?? ''" :parent="{ nom: 'Tenues médicales', lien: '/tenues-medicales' }"
      description="Blouses, tuniques, pantalons et accessoires choisis pour ce métier, brodés à votre nom."
    />
    <ListeProduits :key="slug" :cadre="cadre" />
  </section>
</template>
