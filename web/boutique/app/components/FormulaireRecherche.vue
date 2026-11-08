<script setup lang="ts">
const props = defineProps<{ valeur?: string }>()
const texte = ref(props.valeur ?? '')

function chercher() {
  const q = texte.value.trim()
  if (q) navigateTo({ path: '/recherche', query: { q } })
}
</script>

<template>
  <form class="recherche" role="search" @submit.prevent="chercher">
    <label for="recherche" class="visuellement-cache">Rechercher un produit</label>
    <input id="recherche" v-model="texte" type="search" placeholder="Blouse, t-shirt, kit…" maxlength="100">
    <button type="submit" class="bouton bouton-sourire">Rechercher</button>
  </form>
</template>

<style scoped>
.recherche { display: flex; gap: 8px; max-width: 560px; }
.recherche .bouton { flex-shrink: 0; padding: 0 1.1em; }
.recherche input {
  flex: 1; min-width: 0; min-height: 46px; padding: 0 1em; border: 1.5px solid var(--bordure);
  border-radius: 999px; font: inherit; background: var(--surface);
}
.recherche input:focus { outline: 3px solid var(--primaire-clair); border-color: var(--primaire); }
</style>
