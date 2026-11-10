<script setup lang="ts">
useSeoMeta({ title: 'Broderie et personnalisation', description: 'Votre nom, votre fonction ou le logo de votre structure, brodés à Bamako sur vos blouses, tuniques et calots.' })
const config = useRuntimeConfig()
const whatsapp = computed(() => `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent('Bonjour, je voudrais faire broder le logo de ma structure.')}`)
</script>

<template>
  <section class="conteneur broderie">
    <EnteteListe titre="Broderie et personnalisation" description="Brodé à l'atelier de Bamako, sur la tenue que vous commandez." />

    <div class="exemple carte">
      <div class="poitrine" aria-hidden="true">
        <span class="fil-nom">Aminata Traoré</span>
        <span class="fil-fonction">Sage-femme</span>
      </div>
      <div class="explication">
        <h2>Ce que nous brodons</h2>
        <ul>
          <li><strong>Votre nom et votre fonction</strong>, sur la poitrine, jusqu'à 30 caractères par ligne.</li>
          <li><strong>Le logo de votre structure</strong> : centre de santé, clinique, pharmacie, école.</li>
          <li>En fil bleu, blanc, noir ou aux couleurs de votre logo.</li>
        </ul>
        <p>Indiquez le texte sur la fiche du produit, dans « Texte à broder ». Nous vous montrons un aperçu avant de broder.</p>
      </div>
    </div>

    <div class="etapes">
      <div><h3>1. Vous commandez</h3><p>Choisissez la tenue, la taille, la couleur et écrivez le texte à broder.</p></div>
      <div><h3>2. Nous confirmons</h3><p>Nous vous appelons pour vérifier l'orthographe et vous montrer l'aperçu.</p></div>
      <div><h3>3. L'atelier brode</h3><p>La date de remise vous est donnée à la commande et suivie étape par étape.</p></div>
    </div>

    <div class="carte structures">
      <div>
        <h2>Pour toute une équipe</h2>
        <p>Le logo de votre structure est numérisé une fois, puis brodé sur toutes vos commandes. Demandez un devis avec vos quantités et la répartition des tailles.</p>
      </div>
      <div class="actions">
        <NuxtLink to="/rayons/blouses-medicales" class="bouton">Choisir des blouses</NuxtLink>
        <a :href="whatsapp" target="_blank" rel="noopener" class="bouton bouton-secondaire">Envoyer notre logo</a>
      </div>
    </div>
  </section>
</template>

<style scoped>
.broderie { display: grid; gap: 24px; }
.exemple { display: grid; gap: 24px; padding: 24px; }
@media (min-width: 820px) { .exemple { grid-template-columns: 300px minmax(0, 1fr); align-items: center; } }
.poitrine {
  aspect-ratio: 1; border-radius: var(--rayon); background: #fff; display: grid; place-content: center; gap: 4px;
  text-align: center; box-shadow: inset 0 0 0 1px var(--bordure);
  background-image: repeating-linear-gradient(45deg, transparent 0 6px, rgba(16, 0, 208, 0.03) 6px 7px);
}
.fil-nom { font-size: 1.5rem; font-weight: 800; color: var(--primaire); letter-spacing: 0.02em; }
.fil-fonction { font-size: 1rem; font-weight: 650; color: var(--primaire); }
.explication h2 { margin-top: 0; }
.explication ul { padding-left: 1.2em; display: grid; gap: 6px; }
.etapes { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); }
.etapes h3 { margin: 0 0 6px; color: var(--primaire-fonce); }
.etapes p { margin: 0; color: var(--texte-doux); }
.structures { padding: 24px; display: grid; gap: 16px; background: var(--primaire-clair); border-color: transparent; }
@media (min-width: 820px) { .structures { grid-template-columns: minmax(0, 1fr) auto; align-items: center; } }
.structures h2 { margin-top: 0; }
.structures p { margin: 0; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
