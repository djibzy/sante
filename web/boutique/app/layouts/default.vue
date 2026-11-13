<script setup lang="ts">
import type { Rayon } from '~/types/catalogue'

const config = useRuntimeConfig()
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const tenues = computed(() => (rayons.value ?? []).filter(r => r.univers === 'tenues'))
const whatsapp = computed(() => config.public.whatsapp ? `https://wa.me/${config.public.whatsapp}` : null)
</script>

<template>
  <div class="page">
    <EnTete />
    <BandeauHorsLigne />
    <main>
      <slot />
    </main>
    <section class="reassurance" aria-label="Nos engagements">
      <div class="conteneur reassurance-contenu">
        <div><strong>Brodé à Bamako</strong><span>Dans notre atelier, à votre nom.</span></div>
        <div><strong>Paiement à la livraison</strong><span>Espèces, Orange Money ou Moov Money.</span></div>
        <div><strong>Suivi étape par étape</strong><span>Par SMS et sur votre lien de suivi.</span></div>
        <div><strong>Prix professionnel</strong><span>Pour les soignants et les structures.</span></div>
      </div>
    </section>
    <ChartePied :nom="config.public.nomMarque">
      <div class="colonnes-pied">
        <nav aria-label="Tenues médicales">
          <p class="titre-pied">Tenues médicales</p>
          <NuxtLink v-for="r in tenues" :key="r.slug" :to="`/rayons/${r.slug}`">{{ r.nom }}</NuxtLink>
        </nav>
        <nav aria-label="Services">
          <p class="titre-pied">Services</p>
          <NuxtLink to="/guide-des-tailles">Guide des tailles</NuxtLink>
          <a :href="`${config.public.apiBoutique}/api/v1/catalogue.pdf`" target="_blank" rel="noopener">Télécharger le catalogue (PDF)</a>
          <NuxtLink to="/broderie">Broderie et personnalisation</NuxtLink>
          <NuxtLink to="/services#structures">Devis pour les structures</NuxtLink>
          <NuxtLink to="/services">Nos autres services</NuxtLink>
          <NuxtLink to="/mes-commandes">Suivre ma commande</NuxtLink>
          <NuxtLink to="/hors-ligne">Catalogue hors ligne</NuxtLink>
        </nav>
        <div>
          <p class="titre-pied">Nous joindre</p>
          <p>Bamako, Mali</p>
          <a v-if="whatsapp" :href="whatsapp" target="_blank" rel="noopener">WhatsApp</a>
          <NuxtLink to="/gestion">Espace de l'équipe</NuxtLink>
        </div>
      </div>
      <p>
        Les articles du domaine pharmaceutique ne sont ni vendus ni affichés avec un prix en ligne :
        notre pharmacien partenaire les délivre.
      </p>
      <nav class="liens-legaux" aria-label="Informations légales">
        <NuxtLink to="/conditions">Conditions de vente</NuxtLink>
        <NuxtLink to="/confidentialite">Confidentialité</NuxtLink>
        <NuxtLink to="/mentions-legales">Mentions légales</NuxtLink>
      </nav>
    </ChartePied>
  </div>
</template>

<style scoped>
.reassurance { margin-top: 3rem; background: var(--primaire); color: #fff; }
.reassurance-contenu { display: grid; gap: 16px; padding-top: 22px; padding-bottom: 22px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); }
.reassurance-contenu div { display: grid; gap: 2px; }
.reassurance-contenu span { color: #d9d6ff; font-size: 0.92rem; }
.colonnes-pied { display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr)); margin-bottom: 16px; }
.colonnes-pied nav, .colonnes-pied div { display: grid; gap: 4px; align-content: start; }
.colonnes-pied a { color: var(--texte); text-decoration: none; }
.colonnes-pied a:hover { color: var(--primaire); text-decoration: underline; }
.colonnes-pied p { margin: 0; }
.titre-pied { font-weight: 800; color: var(--texte) !important; margin-bottom: 4px !important; }
.liens-legaux { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 8px 0; }
.liens-legaux a { color: var(--texte-doux); }
</style>
