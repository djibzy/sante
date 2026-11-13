<script setup lang="ts">
// Cadre des textes juridiques. Tant que NUXT_PUBLIC_TEXTES_JURIDIQUES_VALIDES n'est pas « true »,
// un bandeau rappelle qu'il s'agit d'un projet à faire valider par un juriste.
defineProps<{ titre: string, miseAJour: string }>()
const config = useRuntimeConfig()
const valides = computed(() => String(config.public.textesJuridiquesValides) === 'true')
</script>

<template>
  <article class="conteneur juridique">
    <h1>{{ titre }}</h1>
    <p class="aide">Mise à jour le {{ miseAJour }}.</p>
    <p v-if="!valides" class="alerte alerte-info" role="note">
      Projet de texte, fidèle au fonctionnement du site, à faire valider par un juriste avant
      l'ouverture. Les mentions entre crochets sont à compléter.
    </p>
    <slot />
  </article>
</template>

<style scoped>
.juridique { max-width: 760px; padding-top: 24px; padding-bottom: 24px; }
.juridique :deep(h2) { font-size: 1.2rem; margin: 28px 0 8px; }
.juridique :deep(p), .juridique :deep(li) { line-height: 1.6; }
.juridique :deep(ul) { padding-left: 1.2em; }
.juridique :deep(table) { border-collapse: collapse; width: 100%; font-size: 0.95rem; }
.juridique :deep(th), .juridique :deep(td) { text-align: left; padding: 6px 8px 6px 0; border-bottom: 1px solid var(--bordure); vertical-align: top; }
</style>
