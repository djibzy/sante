// Couche commune à toutes les interfaces : couleurs, typographie, composants de base.
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const dossier = dirname(fileURLToPath(import.meta.url))

export default defineNuxtConfig({
  css: [join(dossier, './app/assets/css/charte.css')],
})
