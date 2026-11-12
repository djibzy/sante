/*
 * Bibou hors ligne (service worker). Généré à la construction (nuxt.config.ts) : la liste des
 * fichiers de l'application et la version remplacent les deux marqueurs ci-dessous.
 *
 * - Fichiers de l'application (/_nuxt/), logos et icônes : gardés dès l'installation.
 * - Pages : réseau d'abord (4 secondes), sinon la copie gardée, sinon le catalogue enregistré.
 * - Catalogue public (rayons, métiers, produits, avis, zones) : réseau d'abord, sinon la copie.
 * - Photos : gardées à la première vue (les 120 dernières).
 * - Jamais gardé : suivi des commandes, compte, espace de l'équipe, et tout envoi (POST…).
 */
const VERSION = '__BIBOU_VERSION__'
const FICHIERS = __BIBOU_FICHIERS__
const GARDES_A_L_INSTALLATION = new Set(FICHIERS)
const COQUILLE = `bibou-coquille-${VERSION}`
const PAGES = `bibou-pages-${VERSION}`
const DONNEES = 'bibou-donnees'
const PHOTOS = 'bibou-photos'
const HORS_LIGNE = '/hors-ligne'
const DELAI_RESEAU = 4000
const PHOTOS_MAX = 120
const API_PUBLIQUE = /^\/api\/v1\/(rayons|metiers|zones-livraison|produits)(\/|$)/
const PAGES_PRIVEES = /^\/(suivi|mes-commandes|gestion|atelier|connexion|inscription)(\/|$)/
const MESSAGE_HORS_LIGNE = "Vous êtes hors ligne, et cette page n'est pas enregistrée sur votre téléphone."

self.addEventListener('install', (evenement) => {
  evenement.waitUntil((async () => {
    const cache = await caches.open(COQUILLE)
    await cache.addAll(['/', HORS_LIGNE, '/panier', '/commande', '/devis', ...FICHIERS])
    await self.skipWaiting()
  })())
})

self.addEventListener('activate', (evenement) => {
  evenement.waitUntil((async () => {
    // Les pages et fichiers d'une version précédente renvoient à d'anciens fichiers : on les
    // retire. Les données du catalogue et les photos restent valables d'une version à l'autre.
    const gardes = new Set([COQUILLE, PAGES, DONNEES, PHOTOS])
    for (const nom of await caches.keys()) {
      if (nom.startsWith('bibou-') && !gardes.has(nom)) await caches.delete(nom)
    }
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', (evenement) => {
  const requete = evenement.request
  if (requete.method !== 'GET') return
  const url = new URL(requete.url)
  const ici = url.origin === self.location.origin
  if (requete.mode === 'navigate') {
    if (ici && !PAGES_PRIVEES.test(url.pathname)) evenement.respondWith(page(evenement, url))
  } else if (ici && GARDES_A_L_INSTALLATION.has(url.pathname)) {
    evenement.respondWith(fichier(requete))
  } else if (API_PUBLIQUE.test(url.pathname)) {
    // Même adresse que le site en production ; autre port en développement.
    evenement.respondWith(donnees(evenement, url))
  } else if (ici && url.pathname.startsWith('/medias/')) {
    evenement.respondWith(photo(requete))
  }
})

// « Enregistrer le catalogue » : la page envoie la liste des adresses à garder.
self.addEventListener('message', (evenement) => {
  if (evenement.data?.type !== 'enregistrer' || !evenement.ports[0]) return
  evenement.waitUntil(enregistrer(evenement.data.adresses, evenement.ports[0]))
})

function attendre(ms) {
  return new Promise(resolve => setTimeout(resolve, ms, null))
}

/** Clé de cache indépendante de l'ordre des paramètres (?rayon=…&page=… ou ?page=…&rayon=…). */
function cle(url) {
  const copie = new URL(url)
  copie.searchParams.sort()
  return copie.href
}

/** Réseau d'abord ; s'il tarde, la copie gardée ; sans copie, on attend le réseau. */
async function reseauDabord(evenement, nomCache, cleCache, garder) {
  const cache = await caches.open(nomCache)
  const reseau = fetch(evenement.request).then(async (reponse) => {
    if (garder(reponse)) await cache.put(cleCache, reponse.clone())
    return reponse
  })
  evenement.waitUntil(reseau.then(() => undefined, () => undefined))
  try {
    const rapide = await Promise.race([reseau, attendre(DELAI_RESEAU)])
    if (rapide) return rapide
  } catch {
    // réseau coupé : la copie gardée, s'il y en a une
  }
  const garde = await caches.match(cleCache, { ignoreVary: true })
  if (garde) return garde
  try {
    return await reseau
  } catch {
    return null
  }
}

async function page(evenement, url) {
  const reponse = await reseauDabord(evenement, PAGES, url.href, r => r.ok && (r.headers.get('content-type') ?? '').includes('text/html'))
  if (reponse) return reponse
  if (url.pathname === HORS_LIGNE) {
    const catalogue = await caches.match(HORS_LIGNE, { ignoreVary: true })
    return catalogue ?? new Response(`<!doctype html><meta charset="utf-8"><title>Hors ligne</title><p>${MESSAGE_HORS_LIGNE}</p>`, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    })
  }
  return Response.redirect(`${HORS_LIGNE}?depuis=${encodeURIComponent(url.pathname)}`, 302)
}

async function donnees(evenement, url) {
  const reponse = await reseauDabord(evenement, DONNEES, cle(url), r => r.ok)
  return reponse ?? new Response(JSON.stringify({ detail: MESSAGE_HORS_LIGNE }), {
    status: 503, headers: { 'Content-Type': 'application/json' },
  })
}

async function fichier(requete) {
  const garde = await caches.match(requete, { ignoreVary: true })
  if (garde) return garde
  const reponse = await fetch(requete)
  if (reponse.ok) await (await caches.open(COQUILLE)).put(requete, reponse.clone())
  return reponse
}

async function photo(requete) {
  const cache = await caches.open(PHOTOS)
  const garde = await cache.match(requete.url, { ignoreVary: true })
  if (garde) return garde
  try {
    const reponse = await fetch(requete)
    if (reponse.ok) {
      await cache.put(requete.url, reponse.clone())
      const cles = await cache.keys()
      for (const ancienne of cles.slice(0, Math.max(0, cles.length - PHOTOS_MAX))) await cache.delete(ancienne)
    }
    return reponse
  } catch {
    return Response.error()
  }
}

async function enregistrer(adresses, port) {
  const cache = await caches.open(DONNEES)
  let faites = 0
  let echecs = 0
  for (const adresse of adresses) {
    const url = new URL(adresse, self.location.origin)
    try {
      if (!API_PUBLIQUE.test(url.pathname)) throw new Error('adresse refusée')
      const reponse = await fetch(url.href)
      if (!reponse.ok) throw new Error(String(reponse.status))
      await cache.put(cle(url), reponse)
    } catch {
      echecs += 1
    }
    faites += 1
    port.postMessage({ faites, total: adresses.length, echecs })
  }
}
