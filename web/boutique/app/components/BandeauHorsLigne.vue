<script setup lang="ts">
const { enLigne } = useHorsLigne()
</script>

<template>
  <div v-if="!enLigne" class="hors-ligne" role="status">
    <div class="conteneur contenu">
      <strong>Hors ligne.</strong>
      <span>Vous consultez les pages enregistrées sur ce téléphone ; votre panier est gardé.</span>
      <NuxtLink to="/hors-ligne">Catalogue enregistré</NuxtLink>
    </div>
  </div>
</template>

<style scoped>
.hors-ligne { background: var(--accent-clair); color: var(--accent-texte); border-bottom: 1px solid var(--bordure); }
.contenu { display: flex; flex-wrap: wrap; gap: 4px 10px; padding-top: 8px; padding-bottom: 8px; font-size: 0.92rem; }
.contenu a { color: var(--accent-texte); font-weight: 700; }
</style>
