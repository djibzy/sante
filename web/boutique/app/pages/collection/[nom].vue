<script setup lang="ts">
const route = useRoute()
const nom = computed(() => String(route.params.nom))
const cadre = computed(() => ({ collection: nom.value }))
const DESCRIPTIONS: Record<string, string> = {
  Wax: 'Des empiècements en wax sur des tissus techniques : la tenue médicale à la mode de chez nous.',
  Essentielle: 'Les basiques de tous les jours, robustes et faciles à entretenir.',
  'Confort stretch': 'Des tissus extensibles et légers pour les longues gardes.',
}
useSeoMeta({ title: () => `Collection ${nom.value}` })
</script>

<template>
  <section class="conteneur">
    <EnteteListe :titre="`Collection ${nom}`" :description="DESCRIPTIONS[nom]" :parent="{ nom: 'Tenues médicales', lien: '/tenues-medicales' }" />
    <ListeProduits :key="nom" :cadre="cadre" />
  </section>
</template>
