/**
 * Consignes aux moteurs de recherche : le catalogue est public ; le panier, les commandes, les
 * comptes et l'espace de l'équipe ne sont pas à indexer.
 */
const PRIVES = [
  '/gestion', '/atelier', '/panier', '/commande$', '/suivi', '/mes-commandes', '/mon-compte',
  '/connexion', '/inscription', '/mot-de-passe-oublie', '/devis', '/hors-ligne', '/favoris',
]

export default defineEventHandler((event) => {
  const origine = getRequestURL(event, { xForwardedHost: true, xForwardedProto: true }).origin
  setResponseHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  return ['User-agent: *', ...PRIVES.map(c => `Disallow: ${c}`), '', `Sitemap: ${origine}/sitemap.xml`, ''].join('\n')
})
