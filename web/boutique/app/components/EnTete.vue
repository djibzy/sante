<script setup lang="ts">
import type { Metier, Rayon } from '~/types/catalogue'

// En-tête de boutique spécialisée : bandeau d'annonce, recherche, menu « Tenues médicales »
// (par type, par métier) et menu mobile.
const route = useRoute()
const { nombre } = usePanier()
const { nombre: favoris } = useFavoris()
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const tenues = computed(() => (rayons.value ?? []).filter(r => r.univers === 'tenues'))
const metiersActifs = computed(() => (metiers.value ?? []).filter(m => m.nombre_produits))
const menuTenues = ref(false)
const tiroir = ref(false)

watch(() => route.fullPath, () => {
  menuTenues.value = false
  tiroir.value = false
})
function fermer(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    menuTenues.value = false
    tiroir.value = false
  }
}
onMounted(() => window.addEventListener('keydown', fermer))
onBeforeUnmount(() => window.removeEventListener('keydown', fermer))

const LIENS = [
  { nom: 'Nouveautés', lien: '/nouveautes' },
  { nom: 'Par couleur', lien: '/explorer' },
  { nom: 'Promotions', lien: '/promotions' },
  { nom: 'Kits et matériel', lien: '/univers/equipement' },
  { nom: 'Campagnes', lien: '/rayons/campagnes' },
  { nom: 'Broderie', lien: '/broderie' },
  { nom: 'Structures et devis', lien: '/services#structures' },
]
</script>

<template>
  <div class="annonce">
    <div class="conteneur annonce-contenu">
      <span>Brodé à votre nom à Bamako</span>
      <span class="secondaire">Paiement à la livraison</span>
      <span class="secondaire">Devis pour les structures de santé</span>
    </div>
  </div>
  <header class="entete">
    <div class="conteneur ligne-haute">
      <button type="button" class="burger" aria-label="Ouvrir le menu" :aria-expanded="tiroir" @click="tiroir = true">
        <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" /></svg>
      </button>
      <NuxtLink to="/" class="lien-logo" aria-label="Bibou, accueil de la boutique">
        <img src="/marque/bibou.png" alt="Bibou" width="115" height="44" class="logo">
        <span class="endossement">par Yasal Santé</span>
      </NuxtLink>
      <FormulaireRecherche class="recherche-entete" />
      <nav aria-label="Mon espace" class="mon-espace">
        <NuxtLink to="/favoris" class="bouton bouton-discret lien-favoris" :aria-label="`Favoris (${favoris})`">
          <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-9.2-8.6C1.3 8.4 3 5 6.4 5c2 0 3.4 1.2 4 2.3.6-1.1 2-2.3 4-2.3C17.9 5 20 8 18.6 11.4 16.9 15.6 12 20 12 20z" /></svg>
          <span v-if="favoris" class="nombre-favoris">{{ favoris }}</span>
        </NuxtLink>
        <NuxtLink to="/mes-commandes" class="bouton bouton-discret lien-commandes"><span class="long">Mes commandes</span><span class="court">Commandes</span></NuxtLink>
        <NuxtLink to="/panier" class="bouton lien-panier">
          Panier
          <span class="compteur" :class="{ vide: !nombre }">{{ nombre }}</span>
          <span class="visuellement-cache">articles</span>
        </NuxtLink>
      </nav>
    </div>

    <nav class="conteneur menu" aria-label="Rayons" @mouseleave="menuTenues = false">
      <button type="button" class="entree" :aria-expanded="menuTenues" @click="menuTenues = !menuTenues" @mouseenter="menuTenues = true">
        Tenues médicales
        <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4l4 4 4-4" stroke="currentColor" stroke-width="1.8" fill="none" /></svg>
      </button>
      <NuxtLink v-for="l in LIENS" :key="l.lien" :to="l.lien" class="entree">{{ l.nom }}</NuxtLink>

      <div v-if="menuTenues" class="mega">
        <div>
          <p class="titre-colonne">Par type</p>
          <NuxtLink v-for="r in tenues" :key="r.slug" :to="`/rayons/${r.slug}`">{{ r.nom }}</NuxtLink>
          <NuxtLink to="/tenues-medicales" class="tout">Toutes les tenues</NuxtLink>
        </div>
        <div>
          <p class="titre-colonne">Par métier</p>
          <NuxtLink v-for="m in metiersActifs" :key="m.slug" :to="`/metiers/${m.slug}`">{{ m.nom }}</NuxtLink>
        </div>
        <div>
          <p class="titre-colonne">À découvrir</p>
          <NuxtLink to="/explorer">Explorer par couleur</NuxtLink>
          <NuxtLink to="/composer">Composer ma tenue</NuxtLink>
          <NuxtLink to="/nouveautes">Nouveautés</NuxtLink>
          <NuxtLink to="/collection/Wax">La collection wax</NuxtLink>
          <NuxtLink to="/guide-des-tailles">Guide des tailles</NuxtLink>
          <NuxtLink to="/broderie">Faire broder sa tenue</NuxtLink>
        </div>
      </div>
    </nav>
  </header>

  <div v-if="tiroir" class="voile" @click="tiroir = false" />
  <aside v-if="tiroir" class="tiroir" aria-label="Menu">
    <div class="tiroir-haut">
      <img src="/marque/bibou.png" alt="Bibou" width="94" height="36">
      <button type="button" class="bouton bouton-discret" @click="tiroir = false">Fermer</button>
    </div>
    <FormulaireRecherche />
    <details open>
      <summary>Tenues médicales</summary>
      <NuxtLink v-for="r in tenues" :key="r.slug" :to="`/rayons/${r.slug}`">{{ r.nom }}</NuxtLink>
    </details>
    <details>
      <summary>Par métier</summary>
      <NuxtLink v-for="m in metiersActifs" :key="m.slug" :to="`/metiers/${m.slug}`">{{ m.nom }}</NuxtLink>
    </details>
    <NuxtLink v-for="l in LIENS" :key="l.lien" :to="l.lien" class="lien-tiroir">{{ l.nom }}</NuxtLink>
    <NuxtLink to="/composer" class="lien-tiroir">Composer ma tenue</NuxtLink>
    <NuxtLink to="/guide-des-tailles" class="lien-tiroir">Guide des tailles</NuxtLink>
    <NuxtLink to="/favoris" class="lien-tiroir">Mes favoris</NuxtLink>
  </aside>
</template>

<style scoped>
.annonce { background: var(--primaire-fonce); color: #fff; font-size: 0.85rem; }
.annonce-contenu { display: flex; justify-content: center; gap: 36px; padding-top: 7px; padding-bottom: 7px; }
@media (max-width: 720px) { .annonce .secondaire { display: none; } }
.entete { background: var(--surface); border-bottom: 1px solid var(--bordure); position: sticky; top: 0; z-index: 20; }
.ligne-haute { display: flex; align-items: center; gap: 12px; min-height: 66px; }
.burger { display: none; flex-shrink: 0; padding: 8px; border: 0; background: transparent; color: var(--texte); cursor: pointer; }
.burger svg { width: 24px; max-width: none; }
.lien-logo { display: flex; align-items: flex-end; gap: 10px; text-decoration: none; flex-shrink: 0; }
.logo { height: 40px; width: auto; }
.endossement { color: var(--texte-doux); font-size: 0.8rem; padding-bottom: 4px; white-space: nowrap; }
.recherche-entete { flex: 1; max-width: 460px; margin: 0 auto; }
.mon-espace { display: flex; align-items: center; gap: 4px; margin-left: auto; }
.lien-commandes { white-space: nowrap; }
.lien-favoris { position: relative; padding: 0 0.6em; }
.lien-favoris svg { fill: none; stroke: currentColor; stroke-width: 1.8; max-width: none; }
.nombre-favoris {
  position: absolute; top: 4px; right: 0; min-width: 18px; height: 18px; border-radius: 999px; padding: 0 4px;
  background: var(--accent); color: var(--texte); font-size: 0.72rem; font-weight: 800; display: grid; place-items: center;
}
.lien-commandes .court { display: none; }
.lien-panier { padding: 0 0.9em 0 1.1em; }
.compteur {
  min-width: 24px; height: 24px; padding: 0 6px; border-radius: 999px; display: inline-grid; place-items: center;
  background: var(--accent); color: var(--texte); font-size: 0.82rem; font-weight: 800;
}
.compteur.vide { background: rgba(255, 255, 255, 0.25); color: #fff; }
.menu { display: flex; gap: 2px; position: relative; padding-bottom: 6px; overflow-x: auto; }
.entree {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border: 0; border-radius: 8px;
  background: transparent; font: inherit; font-weight: 650; color: var(--texte); text-decoration: none; white-space: nowrap; cursor: pointer;
}
.entree:hover, .entree[aria-expanded='true'], .entree.router-link-active { background: var(--primaire-clair); color: var(--primaire-fonce); }
.mega {
  position: absolute; top: 100%; left: 16px; right: 16px; z-index: 30; display: grid; gap: 24px;
  grid-template-columns: repeat(3, minmax(0, 1fr)); padding: 22px 26px; background: var(--surface);
  border: 1px solid var(--bordure); border-radius: 0 0 var(--rayon) var(--rayon); box-shadow: var(--ombre);
}
.mega div { display: grid; gap: 4px; align-content: start; }
.mega a { color: var(--texte); text-decoration: none; padding: 4px 0; }
.mega a:hover { color: var(--primaire); }
.titre-colonne { margin: 0 0 6px; font-weight: 800; color: var(--primaire-fonce); }
.mega .tout { font-weight: 700; color: var(--primaire); }
@media (max-width: 900px) {
  .burger { display: block; }
  .menu, .recherche-entete, .endossement { display: none; }
  .ligne-haute { gap: 6px; }
}
@media (max-width: 440px) {
  .lien-favoris { display: none; }
  .lien-commandes .long { display: none; }
  .lien-commandes .court { display: inline; }
  .lien-commandes { padding: 0 0.4em; font-size: 0.92rem; }
  .lien-panier { padding: 0 0.6em 0 0.8em; gap: 6px; }
  .logo { height: 34px; }
  .burger { padding: 6px 4px; }
}
.voile { position: fixed; inset: 0; background: rgba(23, 21, 58, 0.45); z-index: 40; }
.tiroir {
  position: fixed; inset: 0 auto 0 0; width: min(86vw, 360px); z-index: 50; background: var(--surface);
  padding: 16px; display: grid; gap: 10px; align-content: start; overflow-y: auto;
}
.tiroir-haut { display: flex; justify-content: space-between; align-items: center; }
.tiroir details { border-bottom: 1px solid var(--bordure); padding: 6px 0; }
.tiroir summary { font-weight: 750; padding: 8px 0; cursor: pointer; }
.tiroir details a { display: block; padding: 8px 12px; color: var(--texte); text-decoration: none; }
.lien-tiroir { padding: 10px 0; font-weight: 650; color: var(--texte); text-decoration: none; border-bottom: 1px solid var(--bordure); }
</style>
