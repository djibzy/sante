<script setup lang="ts">
const config = useRuntimeConfig()
const { nombre } = usePanier()
</script>

<template>
  <div class="page">
    <header class="entete">
      <div class="conteneur entete-contenu">
        <NuxtLink to="/" class="lien-logo" aria-label="Bibou, accueil de la boutique">
          <img src="/marque/bibou.png" alt="Bibou" width="115" height="44" class="logo">
          <span class="endossement">par Yasal Santé</span>
        </NuxtLink>
        <nav aria-label="Mon espace" class="navigation">
          <NuxtLink to="/mes-commandes" class="bouton bouton-discret lien-commandes"><span class="long">Mes commandes</span><span class="court">Commandes</span></NuxtLink>
          <NuxtLink to="/panier" class="bouton lien-panier">
            Panier
            <span class="compteur" :class="{ vide: !nombre }">{{ nombre }}</span>
            <span class="visuellement-cache">articles</span>
          </NuxtLink>
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
      <p><NuxtLink to="/gestion">Espace de l'équipe</NuxtLink></p>
    </ChartePied>
  </div>
</template>

<style scoped>
.entete { background: var(--surface); border-bottom: 1px solid var(--bordure); position: sticky; top: 0; z-index: 10; }
.entete-contenu { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 66px; }
.lien-logo { display: flex; align-items: flex-end; gap: 10px; text-decoration: none; flex-shrink: 0; }
.logo { height: 40px; width: auto; }
.endossement { color: var(--texte-doux); font-size: 0.8rem; padding-bottom: 4px; white-space: nowrap; }
.navigation { display: flex; align-items: center; gap: 4px; }
.lien-panier { padding: 0 0.9em 0 1.1em; }
.compteur {
  min-width: 24px; height: 24px; padding: 0 6px; border-radius: 999px; display: inline-grid; place-items: center;
  background: var(--accent); color: var(--texte); font-size: 0.82rem; font-weight: 800;
}
.compteur.vide { background: rgba(255, 255, 255, 0.25); color: #fff; }
@media (max-width: 560px) { .endossement { display: none; } }
.lien-commandes { white-space: nowrap; }
.lien-commandes .court { display: none; }
@media (max-width: 440px) {
  .lien-commandes .long { display: none; }
  .lien-commandes .court { display: inline; }
  .lien-commandes { padding: 0 0.5em; }
}
</style>
