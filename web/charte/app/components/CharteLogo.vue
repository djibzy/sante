<script setup lang="ts">
defineProps<{ nom: string; sousTitre?: string }>()
</script>

<template>
  <span class="logo">
    <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--primaire)" />
      <path d="M13 8h6v5h5v6h-5v5h-6v-5H8v-6h5z" fill="#fff" />
    </svg>
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
