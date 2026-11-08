<script setup lang="ts">
// Enveloppe des écrans de l'équipe : attend la session, puis affiche le contenu ou l'invitation.
const route = useRoute()
const { verifie, autorise, utilisateur } = useEquipe()
</script>

<template>
  <p v-if="!verifie" class="aide">Chargement…</p>
  <slot v-else-if="autorise" />
  <div v-else class="carte refus">
    <h1>Espace de l'équipe Bibou</h1>
    <p v-if="utilisateur">Ce compte n'a pas accès à la gestion des commandes.</p>
    <p v-else>Connectez-vous avec un compte de l'équipe.</p>
    <NuxtLink v-if="!utilisateur" :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
  </div>
</template>

<style scoped>
.refus { padding: 24px; max-width: 520px; display: grid; justify-items: start; gap: 4px; }
</style>
