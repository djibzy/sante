<script setup lang="ts">
const config = useRuntimeConfig()
useSeoMeta({
  title: 'Services aux structures de santé',
  description: 'Entretien du linge, tenues de l\'équipe, identité de votre structure : Yasal Santé prend en charge ce qui éloigne vos équipes des soins.',
})
const boutique = config.public.siteBoutique
const SERVICES = [
  {
    titre: 'Entretien du linge',
    texte: 'Tenues, draps, alèses, serviettes : collectés chez vous, lavés par une blanchisserie partenaire, rendus propres et comptés pièce par pièce.',
    lien: '/entretien-du-linge',
    action: 'Découvrir le service',
    nouveau: true,
  },
  {
    titre: 'Les tenues de votre équipe',
    texte: 'Blouses et tuniques brodées au nom de chacun, au prix professionnel, avec un devis à votre logo.',
    lien: `${boutique}/commande-equipe`,
    action: 'Habiller une équipe',
    nouveau: false,
  },
  {
    titre: 'Votre structure à vos couleurs',
    texte: 'Déposez votre logo : sa palette, la peinture la plus proche pour vos murs, votre équipe habillée aux mêmes couleurs.',
    lien: `${boutique}/a-vos-couleurs`,
    action: 'Essayer avec votre logo',
    nouveau: false,
  },
]
</script>

<template>
  <div class="conteneur accueil">
    <section class="ouverture">
      <p class="surtitre">Cliniques, CSCom, cabinets, maternités, laboratoires</p>
      <h1>Des services pensés pour les structures de santé</h1>
      <p class="chapeau">Nous prenons en charge ce qui éloigne vos équipes des soins, avec des partenaires choisis et vérifiés à Bamako.</p>
    </section>
    <section class="services" aria-label="Nos services">
      <article v-for="s in SERVICES" :key="s.titre" class="carte service">
        <span v-if="s.nouveau" class="pastille">Nouveau</span>
        <h2>{{ s.titre }}</h2>
        <p>{{ s.texte }}</p>
        <NuxtLink v-if="s.lien.startsWith('/')" :to="s.lien" class="bouton">{{ s.action }}</NuxtLink>
        <a v-else :href="s.lien" class="bouton bouton-secondaire">{{ s.action }}</a>
      </article>
    </section>
    <p class="suite aide">D'autres services aux structures rejoignent bientôt cette page, avec le même interlocuteur et le même compte.</p>
  </div>
</template>

<style scoped>
.accueil { display: grid; gap: 24px; }
.ouverture { max-width: 760px; padding: 16px 0 4px; }
.surtitre { color: var(--primaire); font-weight: 700; margin-bottom: 0.4em; }
.chapeau { font-size: 1.15rem; color: var(--texte-doux); }
.services { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); }
.service { padding: 20px; display: grid; gap: 10px; align-content: start; justify-items: start; }
.service h2 { margin: 0; font-size: 1.25rem; }
.service p { margin: 0; color: var(--texte-doux); }
.suite { margin: 0; }
</style>
