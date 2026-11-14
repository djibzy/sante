<script setup lang="ts">
import type { Metier, PageProduits, Rayon } from '~/types/catalogue'
import type { Exploration } from '~/types/explorer'

useSeoMeta({ title: 'Tenues médicales brodées à votre nom', description: 'Blouses, tuniques, pantalons et accessoires pour tous les métiers de la santé, fabriqués et brodés à Bamako. Paiement à la livraison.' })
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const { data: nouveautes } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', { query: { nouveau: true, tri: 'nouveautes', par_page: 4 } })
const { data: essentiels } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', { query: { collection: 'Essentielle', par_page: 4 } })
const { data: nuancier } = await useBoutiqueFetch<Exploration>('/api/v1/explorer', { query: { familles_seulement: true } })
const familles = computed(() => (nuancier.value?.familles ?? []).filter(f => f.nombre))
const tenues = computed(() => (rayons.value ?? []).filter(r => r.univers === 'tenues'))
const compteSupprime = useRoute().query.compte === 'supprime'
const config = useRuntimeConfig()
const AUTRES = [
  { titre: 'Kits de soins', texte: 'Hygiène, premiers secours, relais communautaires.', lien: '/rayons/kits', picto: 'kits' },
  { titre: 'Matériel médical', texte: 'Thermomètres, tensiomètres, et le pharmacien partenaire.', lien: '/rayons/materiel-medical', picto: 'materiel-medical' },
  { titre: 'Campagnes de sensibilisation', texte: 'T-shirts, affiches et boîtes à images avec notre studio.', lien: '/rayons/campagnes', picto: 'campagnes' },
  { titre: 'Votre structure à vos couleurs', texte: 'Votre logo : la peinture de vos murs et les tenues de votre équipe.', lien: '/a-vos-couleurs', picto: 'blouses-medicales' },
  { titre: 'Entretien du linge', texte: 'Tenues et draps collectés, lavés, rendus comptés pièce par pièce.', lien: `${config.public.sitePrestations}/entretien-du-linge`, picto: 'entretien' },
]
</script>

<template>
  <div>
    <p v-if="compteSupprime" class="conteneur alerte alerte-succes au-revoir" role="status">
      Votre compte est supprimé. Merci d'avoir fait confiance à Bibou.
    </p>
    <section class="bandeau">
      <div class="conteneur bandeau-contenu">
        <div>
          <h1>La tenue médicale qui vous ressemble, brodée à votre nom</h1>
          <p>Blouses, tuniques et pantalons pour tous les métiers de la santé, fabriqués et brodés à Bamako. Paiement à la livraison.</p>
          <div class="appels">
            <NuxtLink to="/rayons/blouses-medicales" class="bouton bouton-sourire">Voir les blouses</NuxtLink>
            <a href="#metiers" class="bouton bouton-clair">Choisir par métier</a>
          </div>
        </div>
        <img src="/marque/papillon-blanc.png" alt="" width="233" height="260" class="papillon">
      </div>
    </section>
    <svg class="sourire" viewBox="0 0 1000 70" preserveAspectRatio="none" aria-hidden="true">
      <path d="M150 6 Q500 120 850 6 Q500 64 150 6 Z" fill="var(--accent)" />
    </svg>

    <section id="metiers" class="conteneur section">
      <div class="titre-section"><h2>Par métier</h2></div>
      <MetiersTuiles :metiers="metiers ?? []" />
    </section>

    <section v-if="familles.length" class="conteneur section">
      <div class="titre-section">
        <h2>Par couleur</h2>
        <NuxtLink to="/explorer">Explorer toutes les couleurs</NuxtLink>
      </div>
      <ul class="couleurs-accueil">
        <li v-for="f in familles" :key="f.code">
          <NuxtLink :to="{ path: '/explorer', query: { famille: f.code } }">
            <span class="disque" :style="{ background: f.hex }" aria-hidden="true" />
            <span>{{ f.nom }}</span>
          </NuxtLink>
        </li>
      </ul>
    </section>

    <section class="conteneur section">
      <div class="titre-section">
        <h2>Nouveautés</h2>
        <NuxtLink to="/nouveautes">Toutes les nouveautés</NuxtLink>
      </div>
      <GrilleProduits :produits="nouveautes?.elements ?? []" />
    </section>

    <section class="conteneur section">
      <div class="titre-section"><h2>Par type de tenue</h2></div>
      <div class="types">
        <NuxtLink v-for="r in tenues" :key="r.slug" :to="`/rayons/${r.slug}`" class="type">
          <ChartePictogramme :type="r.slug" :taille="64" />
          <strong>{{ r.nom }}</strong>
        </NuxtLink>
      </div>
    </section>

    <section class="conteneur section">
      <div class="broderie">
        <div class="poitrine" aria-hidden="true">
          <span class="fil-nom">Dr Oumar Sangaré</span>
          <span class="fil-fonction">Médecin généraliste</span>
        </div>
        <div>
          <h2>Votre nom, votre fonction, le logo de votre structure</h2>
          <p>Écrivez le texte à broder sur la fiche du produit : nous vérifions l'orthographe avec vous et vous montrons un aperçu avant de broder.</p>
          <NuxtLink to="/broderie" class="bouton">Comment ça marche</NuxtLink>
        </div>
      </div>
    </section>

    <section class="conteneur section">
      <div class="titre-section">
        <h2>Les essentiels</h2>
        <NuxtLink to="/collection/Essentielle">Toute la collection</NuxtLink>
      </div>
      <GrilleProduits :produits="essentiels?.elements ?? []" />
    </section>

    <section class="conteneur section">
      <div class="titre-section">
        <h2>Nos autres services</h2>
        <NuxtLink to="/services">Tout voir</NuxtLink>
      </div>
      <div class="autres">
        <NuxtLink v-for="a in AUTRES" :key="a.titre" :to="a.lien" class="carte autre">
          <ChartePictogramme :type="a.picto" :taille="48" />
          <strong>{{ a.titre }}</strong>
          <span>{{ a.texte }}</span>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.au-revoir { margin-top: 16px; }
.bandeau { background: var(--primaire); color: #fff; overflow: hidden; }
.bandeau-contenu { display: grid; grid-template-columns: minmax(0, 1fr); align-items: center; gap: 24px; padding-top: 36px; padding-bottom: 28px; }
@media (min-width: 820px) { .bandeau-contenu { grid-template-columns: minmax(0, 1fr) 260px; padding-top: 52px; } }
.bandeau h1 { max-width: 18ch; }
.bandeau p { max-width: 560px; color: #d9d6ff; font-size: 1.05rem; }
.appels { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
.bouton-clair { background: transparent; color: #fff; border: 1.5px solid rgba(255, 255, 255, 0.7); }
.bouton-clair:hover { background: rgba(255, 255, 255, 0.12); }
.papillon { display: none; width: 233px; height: auto; justify-self: end; }
@media (min-width: 820px) { .papillon { display: block; } }
.sourire { display: block; width: 100%; height: clamp(28px, 6vw, 64px); margin-top: -1px; }
.section { margin-top: 36px; }
.couleurs-accueil { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); }
.couleurs-accueil a { display: grid; justify-items: center; gap: 6px; padding: 10px 4px; border-radius: 14px; color: var(--texte); text-decoration: none; font-size: 0.85rem; font-weight: 650; text-align: center; line-height: 1.25; }
.couleurs-accueil a:hover, .couleurs-accueil a:focus-visible { background: var(--fond-doux); }
.disque { width: 56px; height: 56px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.2), 0 2px 6px rgba(23, 21, 58, 0.12); }
.titre-section { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.titre-section h2 { margin: 0; }
.titre-section a { font-weight: 650; }
.types { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 130px), 1fr)); }
.type { display: grid; justify-items: center; gap: 8px; padding: 16px 10px; text-align: center; color: inherit; text-decoration: none; border-radius: var(--rayon); }
.type:hover { background: var(--fond-doux); }
.broderie { display: grid; gap: 24px; padding: 24px; border-radius: var(--rayon); background: var(--primaire-clair); align-items: center; }
@media (min-width: 820px) { .broderie { grid-template-columns: 280px minmax(0, 1fr); } }
.broderie h2 { margin-top: 0; }
.poitrine { aspect-ratio: 4 / 3; border-radius: var(--rayon); background: #fff; display: grid; place-content: center; gap: 4px; text-align: center; }
.fil-nom { font-size: 1.35rem; font-weight: 800; color: var(--primaire); }
.fil-fonction { font-weight: 650; color: var(--primaire); }
.autres { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 230px), 1fr)); }
.autre { display: grid; gap: 6px; padding: 18px; color: inherit; text-decoration: none; align-content: start; }
.autre:hover { border-color: var(--primaire); }
.autre span { color: var(--texte-doux); font-size: 0.92rem; }
</style>
