// Couche commune à toutes les interfaces : couleurs, typographie, composants de base.
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const dossier = dirname(fileURLToPath(import.meta.url))

// Exécuté dès la lecture de la page, avant les scripts de l'application : sur un réseau lent,
// un formulaire envoyé trop tôt rechargerait la page et perdrait la saisie. L'envoi est retenu,
// puis rejoué une fois la page prête (voir app/plugins/saisie-avant-hydratation.client.ts).
const ENVOI_RETENU = `(function(){var w=window;function f(e){e.preventDefault();w.__envoiRetenu=e.target}
document.addEventListener('submit',f,true);w.__libererEnvois=function(){document.removeEventListener('submit',f,true)}})()`

export default defineNuxtConfig({
  css: [join(dossier, './app/assets/css/charte.css')],
  app: {
    head: {
      script: [{ innerHTML: ENVOI_RETENU, tagPosition: 'head' }],
    },
  },
})
