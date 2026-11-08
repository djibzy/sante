<script setup lang="ts">
// Pied de page commun : chaque produit se présente comme une marque de Yasal Santé.
defineProps<{ nom: string }>()
const annee = new Date().getFullYear()
</script>

<template>
  <footer class="pied">
    <div class="conteneur pied-contenu">
      <img src="/marque/yasal-sante.png" alt="Yasal Santé" width="108" height="32" class="logo-mere">
      <div>
        <p><strong>{{ nom }}</strong>, une marque de Yasal Santé. Bamako, Mali.</p>
        <div class="aide">
          <slot />
          <p>© {{ annee }} Yasal Santé</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.pied { margin-top: 3rem; padding: 2rem 0 2.5rem; border-top: 1px solid var(--bordure); background: var(--fond-doux); }
.pied-contenu { display: grid; gap: 16px; }
@media (min-width: 720px) { .pied-contenu { grid-template-columns: auto 1fr; gap: 32px; align-items: start; } }
.logo-mere { height: 32px; width: auto; }
.pied p { margin: 0 0 0.4em; }
</style>
