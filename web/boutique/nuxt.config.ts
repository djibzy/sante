export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',
  extends: ['../charte'],
  devtools: { enabled: false },
  runtimeConfig: {
    // Adresse de l'API vue depuis le serveur Nuxt (réseau interne en production).
    apiBoutiqueInterne: '',
    public: {
      nomMarque: 'Santé Mali',
      apiBoutique: 'http://localhost:8002',
      apiComptes: 'http://localhost:8001',
      whatsapp: '', // numéro de commande, format international sans « + » (ex. 22376000000)
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      titleTemplate: '%s · Boutique santé',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#0f6b4a' },
        {
          name: 'description',
          content: 'Tenues brodées, imprimés, kits et matériel pour les soignants, les structures de santé et les campagnes.',
        },
      ],
    },
  },
})
