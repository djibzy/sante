<script setup lang="ts">
// Enveloppe des écrans de l'équipe : attend la session, puis affiche le contenu ou l'invitation.
const props = withDefaults(defineProps<{ roles?: string[] }>(), { roles: () => ['boutique:admin'] })
const route = useRoute()
const { verifie, autorise, utilisateur, estGestionnaire } = useEquipe(props.roles)
</script>

<template>
  <p v-if="!verifie" class="aide">Chargement…</p>
  <template v-else-if="autorise">
    <nav class="navigation-equipe" aria-label="Espace de l'équipe">
      <NuxtLink v-if="estGestionnaire" to="/gestion">Commandes</NuxtLink>
      <NuxtLink v-if="estGestionnaire" to="/gestion/livraisons">Livraisons</NuxtLink>
      <NuxtLink to="/atelier">Atelier</NuxtLink>
      <NuxtLink v-if="estGestionnaire" to="/gestion/stock">Stock</NuxtLink>
      <NuxtLink v-if="estGestionnaire" to="/gestion/catalogue">Catalogue</NuxtLink>
    </nav>
    <slot />
  </template>
  <div v-else class="carte refus">
    <h1>Espace de l'équipe Bibou</h1>
    <p v-if="utilisateur">Ce compte n'a pas accès à cet écran.</p>
    <p v-else>Connectez-vous avec un compte de l'équipe.</p>
    <NuxtLink v-if="!utilisateur" :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
  </div>
</template>

<style scoped>
.refus { padding: 24px; max-width: 520px; display: grid; justify-items: start; gap: 4px; }
.navigation-equipe { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--bordure); overflow-x: auto; }
.navigation-equipe a {
  padding: 10px 14px; font-weight: 650; color: var(--texte-doux); text-decoration: none;
  border-bottom: 3px solid transparent; margin-bottom: -1px;
}
.navigation-equipe a.router-link-exact-active { color: var(--primaire); border-bottom-color: var(--primaire); }
</style>
