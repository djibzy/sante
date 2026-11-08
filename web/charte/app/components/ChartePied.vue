<script setup lang="ts">
defineProps<{ nom: string }>()
const annee = new Date().getFullYear()
</script>

<template>
  <footer class="pied">
    <div class="conteneur">
      <p><strong>{{ nom }}</strong> — information, formation et équipement de santé au Mali.</p>
      <p class="aide">
        Les contenus de santé sont validés par notre comité médical. Les produits réservés au
        pharmacien sont délivrés par notre pharmacien partenaire. © {{ annee }}
      </p>
    </div>
  </footer>
</template>

<style scoped>
.pied { margin-top: 3rem; padding: 2rem 0; border-top: 1px solid var(--bordure); background: var(--surface); }
.pied p { margin: 0 0 0.4em; }
</style>
