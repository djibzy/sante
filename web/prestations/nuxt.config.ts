// Interface des prestations aux structures de santé : pages publiques (l'offre, la demande) et
// espace de l'équipe (demandes, contrats, tournée, partenaires, relevés). Aux couleurs de Yasal
// Santé, la marque mère : la charte commune s'applique telle quelle.
import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',
  extends: ['../charte'],
  devtools: { enabled: false },
  css: [fileURLToPath(new URL('./app/assets/css/prestations.css', import.meta.url))],
  runtimeConfig: {
    // Adresse de l'API vue depuis le serveur Nuxt (réseau interne en production).
    apiPrestationsInterne: '',
    public: {
      nomMarque: 'Yasal Santé',
      apiPrestations: 'http://localhost:8003',
      apiComptes: 'http://localhost:8001',
      // La boutique Bibou : tenues de l'équipe, « À vos couleurs », mot de passe oublié.
      siteBoutique: 'http://localhost:3000',
      whatsapp: '', // format international sans « + » (ex. 22376000000)
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      titleTemplate: '%s – Yasal Santé',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#177a4a' },
        {
          name: 'description',
          content: 'Yasal Santé, services aux structures de santé au Mali : entretien du linge (tenues, draps, alèses) avec collecte, lavage par des blanchisseries partenaires et retour compté.',
        },
        { property: 'og:site_name', content: 'Yasal Santé' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { rel: 'apple-touch-icon', href: '/marque/yasal-sante-icone.png' },
      ],
    },
  },
})
