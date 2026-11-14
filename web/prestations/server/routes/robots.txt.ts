/** Consignes aux moteurs de recherche : l'offre est publique, l'espace de l'équipe ne l'est pas. */
export default defineEventHandler((event) => {
  setResponseHeader(event, 'Content-Type', 'text/plain; charset=utf-8')
  return ['User-agent: *', 'Disallow: /equipe', 'Disallow: /connexion', ''].join('\n')
})
