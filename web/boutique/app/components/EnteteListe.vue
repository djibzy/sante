<script setup lang="ts">
// Titre d'une page de liste, avec le fil d'Ariane.
defineProps<{ titre: string; description?: string; pictogramme?: string; parent?: { nom: string; lien: string } }>()
</script>

<template>
  <header class="entete-liste">
    <nav class="fil" aria-label="Fil d'Ariane">
      <NuxtLink to="/">Accueil</NuxtLink>
      <template v-if="parent"> / <NuxtLink :to="parent.lien">{{ parent.nom }}</NuxtLink></template>
    </nav>
    <div class="titre">
      <ChartePictogramme v-if="pictogramme" :type="pictogramme" :taille="56" />
      <div>
        <h1>{{ titre }}</h1>
        <p v-if="description">{{ description }}</p>
      </div>
    </div>
  </header>
</template>

<style scoped>
.entete-liste { padding: 20px 0 8px; }
.fil { color: var(--texte-doux); font-size: 0.9rem; margin-bottom: 10px; }
.fil a { color: inherit; }
.titre { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; }
.titre h1 { margin: 0 0 4px; }
.titre p { margin: 0; color: var(--texte-doux); max-width: 68ch; }
</style>
