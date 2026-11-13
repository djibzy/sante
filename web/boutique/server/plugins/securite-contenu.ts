import { randomBytes } from 'node:crypto'

/**
 * Politique de sécurité du contenu (CSP) des pages. Seuls s'exécutent les scripts du site et ses
 * scripts en ligne, marqués d'un nonce tiré à chaque réponse : un texte injecté dans une page
 * (nom de produit, avis…) ne pourrait pas lancer de script. Les appels ne vont qu'à l'API de la
 * boutique et au service Comptes ; aucune page ne peut être affichée dans le cadre d'un autre site.
 */
const origine = (adresse: string) => {
  try {
    return new URL(adresse).origin
  } catch {
    return '' // adresse relative : même origine que le site
  }
}

export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('render:html', (html, { event }) => {
    const nonce = randomBytes(16).toString('base64')
    const marquer = (morceaux: string[]) =>
      morceaux.map(m => m.replace(/<script\b(?![^>]*\bnonce=)/g, `<script nonce="${nonce}"`))
    html.head = marquer(html.head)
    html.bodyPrepend = marquer(html.bodyPrepend)
    html.body = marquer(html.body)
    html.bodyAppend = marquer(html.bodyAppend)

    const { apiBoutique, apiComptes } = useRuntimeConfig(event).public
    const services = [apiBoutique, apiComptes].map(a => origine(String(a))).filter(Boolean).join(' ')
    const chiffre = services.split(' ').every(o => !o || o.startsWith('https:'))
    setResponseHeader(event, 'Content-Security-Policy', [
      "default-src 'self'",
      `script-src 'self' 'nonce-${nonce}'`,
      "style-src 'self' 'unsafe-inline'", // attributs style des composants
      `img-src 'self' data: blob: https: ${services}`,
      "font-src 'self' data:",
      `connect-src 'self' ${services}`,
      "worker-src 'self'",
      "manifest-src 'self'",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
      ...(chiffre ? ['upgrade-insecure-requests'] : []),
    ].join('; '))
  })
})
