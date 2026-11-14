<script setup lang="ts">
const config = useRuntimeConfig()
const { utilisateur, aLeRole } = useSession()
const equipe = computed(() => aLeRole(GESTION) || aLeRole(TERRAIN))
</script>

<template>
  <div class="page">
    <header class="entete">
      <div class="conteneur entete-contenu">
        <NuxtLink to="/" class="marque">
          <CharteLogo nom="Yasal Santé" sous-titre="Services aux structures de santé" />
        </NuxtLink>
        <nav class="liens" aria-label="Navigation principale">
          <NuxtLink to="/entretien-du-linge">Entretien du linge</NuxtLink>
          <a :href="`${config.public.siteBoutique}/commande-equipe`">Tenues</a>
          <NuxtLink v-if="equipe" to="/equipe">Équipe</NuxtLink>
          <NuxtLink v-else-if="!utilisateur" to="/connexion" class="discret">Espace équipe</NuxtLink>
        </nav>
      </div>
    </header>
    <main>
      <slot />
    </main>
    <ChartePied nom="Yasal Santé – services aux structures">
      <p>
        Entretien du linge avec des blanchisseries partenaires.
        Tenues brodées et identité de votre structure avec
        <a :href="config.public.siteBoutique">Bibou, notre boutique</a>.
      </p>
    </ChartePied>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; display: flex; flex-direction: column; }
main { flex: 1; padding: 24px 0 8px; }
.entete { border-bottom: 1px solid var(--bordure); background: var(--surface); position: sticky; top: 0; z-index: 10; }
.entete-contenu { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 64px; flex-wrap: wrap; padding-block: 8px; }
.marque { text-decoration: none; }
.liens { display: flex; gap: 4px; flex-wrap: wrap; }
.liens a { padding: 8px 10px; border-radius: 8px; font-weight: 650; text-decoration: none; color: var(--texte); }
.liens a:hover, .liens a.router-link-active { background: var(--primaire-clair); color: var(--primaire-fonce); }
.liens .discret { color: var(--texte-doux); font-weight: 500; }
</style>
