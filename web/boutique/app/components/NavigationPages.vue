<script setup lang="ts">
const props = defineProps<{ page: number; total: number; parPage: number }>()
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.parPage)))
const route = useRoute()
const lien = (numero: number) => ({ query: { ...route.query, page: numero } })
</script>

<template>
  <nav v-if="pages > 1" class="pages" aria-label="Pages">
    <NuxtLink v-if="page > 1" :to="lien(page - 1)" class="bouton bouton-secondaire">Précédente</NuxtLink>
    <span>Page {{ page }} sur {{ pages }}</span>
    <NuxtLink v-if="page < pages" :to="lien(page + 1)" class="bouton bouton-secondaire">Suivante</NuxtLink>
  </nav>
</template>

<style scoped>
.pages { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 24px; color: var(--texte-doux); }
</style>
