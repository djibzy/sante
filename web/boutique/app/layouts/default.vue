<script setup lang="ts">
const config = useRuntimeConfig()
const { utilisateur, deconnexion } = useSession()
const prenom = computed(() => utilisateur.value?.nom.split(' ')[0] ?? '')
</script>

<template>
  <div class="page">
    <header class="entete">
      <div class="conteneur entete-contenu">
        <NuxtLink to="/" class="lien-logo">
          <CharteLogo :nom="config.public.nomMarque" sous-titre="Boutique" />
        </NuxtLink>
        <nav aria-label="Compte">
          <template v-if="utilisateur">
            <span class="bonjour">Bonjour, {{ prenom }}</span>
            <button type="button" class="bouton bouton-secondaire" @click="deconnexion">
              Se déconnecter
            </button>
          </template>
          <NuxtLink v-else to="/connexion" class="bouton bouton-secondaire">Se connecter</NuxtLink>
        </nav>
      </div>
    </header>
    <main>
      <slot />
    </main>
    <ChartePied :nom="config.public.nomMarque" />
  </div>
</template>

<style scoped>
.entete { background: var(--surface); border-bottom: 1px solid var(--bordure); position: sticky; top: 0; z-index: 10; }
.entete-contenu { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 64px; }
.lien-logo { text-decoration: none; }
nav { display: flex; align-items: center; gap: 12px; }
.bonjour { color: var(--texte-doux); font-size: 0.95rem; }
@media (max-width: 480px) { .bonjour { display: none; } }
</style>
