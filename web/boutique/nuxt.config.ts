import { fileURLToPath } from 'node:url'

export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',
  extends: ['../charte'],
  devtools: { enabled: false },
  // Après la charte commune : les couleurs de Bibou remplacent celles de Yasal Santé.
  css: [fileURLToPath(new URL('./app/assets/css/bibou.css', import.meta.url))],
  runtimeConfig: {
    // Adresse de l'API vue depuis le serveur Nuxt (réseau interne en production).
    apiBoutiqueInterne: '',
    public: {
      nomMarque: 'Bibou',
      apiBoutique: 'http://localhost:8002',
      apiComptes: 'http://localhost:8001',
      whatsapp: '', // numéro de commande, format international sans « + » (ex. 22376000000)
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      titleTemplate: '%s – Bibou',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#1000d0' },
        {
          name: 'description',
          content: 'Bibou, la boutique de Yasal Santé : tenues brodées, imprimés, kits et matériel pour les soignants et les structures de santé au Mali.',
        },
        { property: 'og:site_name', content: 'Bibou par Yasal Santé' },
        { property: 'og:image', content: '/icone-512.png' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
      ],
    },
  },
})
