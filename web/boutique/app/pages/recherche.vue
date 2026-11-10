<script setup lang="ts">
const route = useRoute()
const q = computed(() => String(route.query.q ?? ''))
const cadre = computed(() => ({ q: q.value }))
useSeoMeta({ title: () => `Recherche : ${q.value}`, robots: 'noindex' })
</script>

<template>
  <section class="conteneur">
    <EnteteListe :titre="q ? `Recherche : « ${q} »` : 'Recherche'" />
    <FormulaireRecherche :key="q" :valeur="q" class="formulaire" />
    <ListeProduits :key="q" :cadre="cadre" />
  </section>
</template>

<style scoped>
.formulaire { margin-bottom: 20px; }
</style>
