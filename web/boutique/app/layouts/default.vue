<script setup lang="ts">
const config = useRuntimeConfig()
const { utilisateur, deconnexion } = useSession()
const prenom = computed(() => utilisateur.value?.nom.split(' ')[0] ?? '')
</script>

<template>
  <div class="page">
    <header class="entete">
      <div class="conteneur entete-contenu">
        <NuxtLink to="/" class="lien-logo" aria-label="Bibou, accueil de la boutique">
          <img src="/marque/bibou.png" alt="Bibou" width="115" height="44" class="logo">
          <span class="endossement">par Yasal Santé</span>
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
    <ChartePied :nom="config.public.nomMarque">
      <p>
        Les articles du domaine pharmaceutique ne sont ni vendus ni affichés avec un prix en ligne :
        notre pharmacien partenaire les délivre.
      </p>
    </ChartePied>
  </div>
</template>

<style scoped>
.entete { background: var(--surface); border-bottom: 1px solid var(--bordure); position: sticky; top: 0; z-index: 10; }
.entete-contenu { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 66px; }
.lien-logo { display: flex; align-items: flex-end; gap: 10px; text-decoration: none; }
.logo { height: 40px; width: auto; }
.endossement { color: var(--texte-doux); font-size: 0.8rem; padding-bottom: 4px; white-space: nowrap; }
nav { display: flex; align-items: center; gap: 12px; }
.bonjour { color: var(--texte-doux); font-size: 0.95rem; }
@media (max-width: 560px) { .endossement, .bonjour { display: none; } }
</style>
