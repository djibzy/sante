import { createHash } from 'node:crypto'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Écrit /sw.js (travail hors ligne) avec la liste des fichiers publics de cette construction :
 * application (/_nuxt/), logos et icônes. */
async function ecrireServiceWorker(dossierPublic: string) {
  const entrees = await readdir(dossierPublic, { recursive: true, withFileTypes: true })
  const fichiers = entrees
    .filter(f => f.isFile())
    .map(f => `/${relative(dossierPublic, join(f.parentPath, f.name)).split(sep).join('/')}`)
    .filter(chemin => chemin !== '/sw.js' && !chemin.startsWith('/.well-known/')
      && chemin !== '/_nuxt/builds/latest.json') // dernière version publiée : toujours relue
    .sort()
  const modele = await readFile(fileURLToPath(new URL('./sw/modele.js', import.meta.url)), 'utf8')
  const version = createHash('sha256').update(modele).update(fichiers.join('\n')).digest('hex').slice(0, 12)
  await writeFile(
    join(dossierPublic, 'sw.js'),
    modele.replace('__BIBOU_VERSION__', () => version).replace('__BIBOU_FICHIERS__', () => JSON.stringify(fichiers)),
  )
}

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
      // « true » une fois les textes juridiques validés par un juriste : retire le bandeau « projet ».
      textesJuridiquesValides: '',
    },
  },
  hooks: {
    'nitro:build:public-assets': nitro => ecrireServiceWorker(nitro.options.output.publicDir),
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
