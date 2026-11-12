<script setup lang="ts">
import type { Metier, PageProduits, ProduitResume, Rayon } from '~/types/catalogue'

// Catalogue enregistré sur l'appareil : consultable sans réseau, avec le panier. Les données
// viennent de l'API ; hors ligne, le service worker répond avec la copie gardée.
useSeoMeta({ title: 'Catalogue hors ligne', robots: 'noindex' })
const route = useRoute()
const config = useRuntimeConfig()
const { enLigne } = useHorsLigne()
const depuis = typeof route.query.depuis === 'string' ? route.query.depuis : ''
const CLE = 'bibou:catalogue-enregistre'
const rayons = ref<Rayon[]>([])
const produits = ref<ProduitResume[]>([])
const chargement = ref(true)
const erreur = ref('')
const enregistre = ref<{ date: string, articles: number } | null>(null)
const progression = ref<{ faites: number, total: number, echecs: number } | null>(null)
const pret = ref(false) // service worker actif : le catalogue peut être enregistré

function lire<T>(chemin: string, query?: Record<string, string | number | boolean>) {
  return $fetch<T>(chemin, { baseURL: config.public.apiBoutique, query })
}

async function chargerCatalogue() {
  chargement.value = true
  try {
    rayons.value = await lire<Rayon[]>('/api/v1/rayons')
    const tous: ProduitResume[] = []
    for (let page = 1; page <= 20; page++) {
      const resultat = await lire<PageProduits>('/api/v1/produits', { page, par_page: 60 })
      tous.push(...resultat.elements)
      if (!resultat.elements.length || tous.length >= resultat.total) break
    }
    produits.value = tous
    erreur.value = ''
  } catch (e) {
    erreur.value = enLigne.value
      ? messageErreur(e)
      : "Le catalogue n'est pas encore enregistré sur ce téléphone. Revenez ici avec du réseau et touchez « Enregistrer le catalogue »."
  } finally {
    chargement.value = false
  }
}

const groupes = computed(() => rayons.value
  .map(rayon => ({ rayon, produits: produits.value.filter(p => p.rayon_slug === rayon.slug) }))
  .filter(g => g.produits.length))

/** Adresses lues par les pages du site, avec les mêmes paramètres, pour les retrouver sans réseau. */
async function adresses(): Promise<string[]> {
  const base = config.public.apiBoutique || window.location.origin
  const url = (chemin: string, query: Record<string, string | number | boolean> = {}) => {
    const adresse = new URL(chemin, base)
    for (const [cle, valeur] of Object.entries(query)) adresse.searchParams.set(cle, String(valeur))
    return adresse.href
  }
  const metiers = await lire<Metier[]>('/api/v1/metiers')
  const liste = { tri: 'pertinence', page: 1, par_page: 24 } // première page d'une liste
  const pages = Math.max(1, Math.ceil(produits.value.length / 60))
  const collections = [...new Set(produits.value.map(p => p.collection).filter((c): c is string => !!c))]
  const univers = [...new Set(rayons.value.map(r => r.univers))]
  return [
    url('/api/v1/rayons'), url('/api/v1/metiers'), url('/api/v1/zones-livraison'),
    ...Array.from({ length: pages }, (_, i) => url('/api/v1/produits', { page: i + 1, par_page: 60 })),
    url('/api/v1/produits', { nouveau: true, tri: 'nouveautes', par_page: 4 }),
    url('/api/v1/produits', { collection: 'Essentielle', par_page: 4 }),
    url('/api/v1/produits', { nouveau: true, ...liste }),
    url('/api/v1/produits', { promo: true, ...liste }),
    ...rayons.value.flatMap(r => [
      url('/api/v1/produits', { rayon: r.slug, ...liste }),
      url('/api/v1/produits', { rayon: r.slug, par_page: 5 }),
    ]),
    ...metiers.map(m => url('/api/v1/produits', { metier: m.slug, ...liste })),
    ...univers.map(u => url('/api/v1/produits', { univers: u, ...liste })),
    ...collections.map(c => url('/api/v1/produits', { collection: c, ...liste })),
    ...produits.value.flatMap(p => [
      url(`/api/v1/produits/${p.slug}`),
      url(`/api/v1/produits/${p.slug}/avis`, { par_page: 5 }),
    ]),
  ]
}

async function enregistrer() {
  erreur.value = ''
  try {
    const liste = await adresses()
    const travailleur = (await navigator.serviceWorker.ready).active
    if (!travailleur) throw new Error('service worker inactif')
    progression.value = { faites: 0, total: liste.length, echecs: 0 }
    const canal = new MessageChannel()
    await new Promise<void>((resolve) => {
      canal.port1.onmessage = ({ data }) => {
        progression.value = data
        if (data.faites >= data.total) resolve()
      }
      travailleur.postMessage({ type: 'enregistrer', adresses: liste }, [canal.port2])
    })
    enregistre.value = { date: new Date().toISOString(), articles: produits.value.length }
    try {
      localStorage.setItem(CLE, JSON.stringify(enregistre.value))
    } catch {
      // navigation privée : l'enregistrement marche, sa date n'est pas retenue
    }
  } catch (e) {
    erreur.value = e instanceof Error && e.message === 'service worker inactif'
      ? "L'enregistrement n'est pas disponible dans ce navigateur."
      : messageErreur(e)
  }
}

onMounted(async () => {
  try {
    const brut = localStorage.getItem(CLE)
    enregistre.value = brut ? JSON.parse(brut) : null
  } catch {
    enregistre.value = null
  }
  pret.value = 'serviceWorker' in navigator && !!(await Promise.race([
    navigator.serviceWorker.ready, new Promise(resolve => setTimeout(resolve, 3000, null)),
  ]))
  await chargerCatalogue()
})
</script>

<template>
  <section class="conteneur hors-ligne">
    <h1>Catalogue hors ligne</h1>
    <p v-if="depuis && !enLigne" class="alerte alerte-info">
      Vous êtes hors ligne et la page demandée n'est pas enregistrée sur ce téléphone. Voici le catalogue enregistré.
    </p>
    <div class="carte enregistrement">
      <p v-if="enregistre">
        Catalogue enregistré le {{ formaterDateHeure(enregistre.date) }} : {{ enregistre.articles }} articles,
        consultables sans réseau. Votre panier est gardé : envoyez votre commande dès le retour du réseau.
      </p>
      <p v-else>
        Enregistrez le catalogue pour le consulter sans réseau (quelques centaines de Ko, sans les photos).
        Les pages et photos déjà vues restent aussi disponibles.
      </p>
      <template v-if="enLigne && pret">
        <button type="button" class="bouton" :disabled="!!progression && progression.faites < progression.total" @click="enregistrer">
          {{ enregistre ? 'Mettre à jour le catalogue enregistré' : 'Enregistrer le catalogue sur ce téléphone' }}
        </button>
        <p v-if="progression" class="aide" role="status">
          <template v-if="progression.faites < progression.total">Enregistrement : {{ progression.faites }} / {{ progression.total }}…</template>
          <template v-else-if="progression.echecs">Enregistré, sauf {{ progression.echecs }} page(s) : réessayez avec un meilleur réseau.</template>
          <template v-else>Catalogue enregistré.</template>
        </p>
      </template>
      <p v-else-if="!enLigne" class="aide">Vous êtes hors ligne : l'enregistrement reprendra avec le réseau.</p>
    </div>

    <p v-if="chargement" class="aide">Chargement du catalogue…</p>
    <p v-else-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
    <section v-for="g in groupes" :key="g.rayon.slug" class="rayon" :aria-labelledby="`rayon-${g.rayon.slug}`">
      <h2 :id="`rayon-${g.rayon.slug}`">{{ g.rayon.nom }}</h2>
      <GrilleProduits :produits="g.produits" />
    </section>
  </section>
</template>

<style scoped>
.hors-ligne { padding-top: 24px; }
.enregistrement { padding: 18px; display: grid; gap: 10px; justify-items: start; margin-bottom: 24px; max-width: 760px; }
.enregistrement p { margin: 0; }
.rayon { margin-top: 28px; }
.rayon h2 { margin-bottom: 12px; }
</style>
