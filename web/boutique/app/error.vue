<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
const introuvable = computed(() => props.error.statusCode === 404)
</script>

<template>
  <NuxtLayout>
    <section class="conteneur erreur">
      <h1>{{ introuvable ? 'Page introuvable' : 'Une erreur est survenue' }}</h1>
      <p>{{ introuvable ? "Cette page n'existe pas ou n'est plus disponible." : 'Réessayez dans un instant.' }}</p>
      <button type="button" class="bouton" @click="clearError({ redirect: '/' })">Retour à l'accueil</button>
    </section>
  </NuxtLayout>
</template>

<style scoped>
.erreur { padding: 64px 16px; text-align: center; }
</style>
