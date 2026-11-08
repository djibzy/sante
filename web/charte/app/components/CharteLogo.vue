<script setup lang="ts">
// Logo de la marque mère, suivi du nom du produit. Les produits qui ont leur propre logo
// (Bibou pour la boutique) l'affichent directement.
defineProps<{ nom: string; sousTitre?: string }>()
</script>

<template>
  <span class="logo">
    <img src="/marque/yasal-sante-icone.png" alt="" width="34" height="34">
    <span>
      <strong>{{ nom }}</strong>
      <small v-if="sousTitre">{{ sousTitre }}</small>
    </span>
  </span>
</template>

<style scoped>
.logo { display: inline-flex; align-items: center; gap: 10px; color: var(--texte); }
.logo strong { display: block; font-size: 1.05rem; line-height: 1.1; }
.logo small { display: block; color: var(--texte-doux); font-size: 0.78rem; }
</style>
