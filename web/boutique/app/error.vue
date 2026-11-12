<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
const { enLigne } = useHorsLigne()
// Sans réseau, une page absente de l'appareil n'est pas « introuvable » : elle n'est pas enregistrée.
const horsLigne = computed(() => props.error.statusCode === 503 || !enLigne.value)
const introuvable = computed(() => props.error.statusCode === 404)
</script>

<template>
  <NuxtLayout>
    <section class="conteneur erreur">
      <template v-if="horsLigne">
        <h1>Vous êtes hors ligne</h1>
        <p>Cette page n'est pas enregistrée sur votre téléphone. Le catalogue enregistré reste consultable.</p>
        <button type="button" class="bouton" @click="clearError({ redirect: '/hors-ligne' })">Voir le catalogue enregistré</button>
      </template>
      <template v-else>
        <h1>{{ introuvable ? 'Page introuvable' : 'Une erreur est survenue' }}</h1>
        <p>{{ introuvable ? "Cette page n'existe pas ou n'est plus disponible." : 'Réessayez dans un instant.' }}</p>
        <button type="button" class="bouton" @click="clearError({ redirect: '/' })">Retour à l'accueil</button>
      </template>
    </section>
  </NuxtLayout>
</template>

<style scoped>
.erreur { padding: 64px 16px; text-align: center; }
</style>
