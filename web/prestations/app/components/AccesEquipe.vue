<script setup lang="ts">
// Enveloppe des écrans de l'équipe : attend la session, puis affiche le contenu ou l'invitation.
// « gestion » : écran réservé à la gestion (prix, contrats, relevés), pas à l'équipe de terrain.
const props = defineProps<{ gestion?: boolean }>()
const route = useRoute()
const { verifie, autorise, estGestionnaire, utilisateur } = useEquipe()
const permis = computed(() => (props.gestion ? estGestionnaire.value : autorise.value))
</script>

<template>
  <p v-if="!verifie" class="aide">Chargement…</p>
  <template v-else-if="permis">
    <nav class="navigation-equipe" aria-label="Espace de l'équipe">
      <NuxtLink to="/equipe">Aujourd'hui</NuxtLink>
      <NuxtLink to="/equipe/tournee">Tournée</NuxtLink>
      <template v-if="estGestionnaire">
        <NuxtLink to="/equipe/demandes">Demandes</NuxtLink>
        <NuxtLink to="/equipe/contrats">Contrats</NuxtLink>
        <NuxtLink to="/equipe/partenaires">Partenaires</NuxtLink>
        <NuxtLink to="/equipe/releves">Relevés</NuxtLink>
      </template>
    </nav>
    <slot />
  </template>
  <div v-else class="carte refus">
    <h1>Espace de l'équipe</h1>
    <p v-if="utilisateur">Ce compte n'a pas accès à cet écran.</p>
    <p v-else>Connectez-vous avec un compte de l'équipe.</p>
    <NuxtLink v-if="!utilisateur" :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
  </div>
</template>

<style scoped>
.refus { padding: 24px; max-width: 520px; display: grid; justify-items: start; gap: 4px; }
.navigation-equipe { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--bordure); overflow-x: auto; }
.navigation-equipe a {
  padding: 10px 14px; font-weight: 650; color: var(--texte-doux); text-decoration: none; white-space: nowrap;
  border-bottom: 3px solid transparent; margin-bottom: -1px;
}
.navigation-equipe a.router-link-exact-active { color: var(--primaire); border-bottom-color: var(--primaire); }
</style>
