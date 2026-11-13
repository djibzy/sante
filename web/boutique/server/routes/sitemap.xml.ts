/**
 * Plan du site pour les moteurs de recherche : pages du catalogue (rayons, métiers, produits)
 * et pages de découverte, lus dans l'API et gardés une heure.
 */
interface Rayon { slug: string, univers: string }
interface Metier { slug: string, nombre_produits: number }
interface Page { elements: { slug: string }[], total: number }

const FIXES = [
  '/', '/tenues-medicales', '/explorer', '/composer', '/commande-equipe', '/nouveautes', '/promotions',
  '/services', '/broderie', '/guide-des-tailles', '/conditions', '/confidentialite', '/mentions-legales',
]
const echapper = (texte: string) => texte.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export default defineCachedEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const baseURL = (config.apiBoutiqueInterne as string) || config.public.apiBoutique
  const lire = <T>(chemin: string, query?: Record<string, string | number>) => $fetch<T>(chemin, { baseURL, query })
  const origine = getRequestURL(event, { xForwardedHost: true, xForwardedProto: true }).origin
  const [rayons, metiers] = await Promise.all([lire<Rayon[]>('/api/v1/rayons'), lire<Metier[]>('/api/v1/metiers')])
  const produits: string[] = []
  for (let page = 1; page <= 50; page++) {
    const resultat = await lire<Page>('/api/v1/produits', { page, par_page: 60 })
    produits.push(...resultat.elements.map(p => p.slug))
    if (!resultat.elements.length || produits.length >= resultat.total) break
  }
  const chemins = [
    ...FIXES,
    ...rayons.map(r => `/rayons/${r.slug}`),
    ...[...new Set(rayons.map(r => r.univers))].map(u => `/univers/${u}`),
    ...metiers.filter(m => m.nombre_produits).map(m => `/metiers/${m.slug}`),
    ...produits.map(slug => `/produits/${slug}`),
  ]
  setResponseHeader(event, 'Content-Type', 'application/xml; charset=utf-8')
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...chemins.map(c => `  <url><loc>${echapper(origine + c)}</loc></url>`),
    '</urlset>',
    '',
  ].join('\n')
}, {
  maxAge: 3600,
  swr: true,
  // Le gestionnaire mis en cache ne reçoit que ces en-têtes : l'adresse publique en dépend.
  varies: ['host', 'x-forwarded-host', 'x-forwarded-proto'],
  getKey: event => getRequestURL(event, { xForwardedHost: true, xForwardedProto: true }).origin,
})
