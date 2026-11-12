<script setup lang="ts">
import type { PageAvis } from '~/types/avis'
import { formaterNote } from '~/types/avis'
import type { Metier, PageProduits, ProduitDetail } from '~/types/catalogue'

const route = useRoute()
const config = useRuntimeConfig()
const { data: produit, error: erreurProduit } = await useBoutiqueFetch<ProduitDetail>(
  () => `/api/v1/produits/${String(route.params.slug)}`,
)
if (!produit.value) {
  // 503 : hors ligne, fiche pas encore enregistrée sur l'appareil.
  const statusCode = erreurProduit.value?.statusCode === 503 ? 503 : 404
  throw createError({ statusCode, statusMessage: 'Produit introuvable', fatal: true })
}
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const { data: voisins } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: { rayon: produit.value.rayon_slug, par_page: 5 },
})
const suggestions = computed(() => (voisins.value?.elements ?? []).filter(p => p.slug !== produit.value?.slug).slice(0, 4))
const { data: avis } = await useBoutiqueFetch<PageAvis>(
  () => `/api/v1/produits/${String(route.params.slug)}/avis`, { query: { par_page: 5 } },
)

// Choix en deux temps, comme en boutique : la couleur, puis la taille.
const couleur = ref<string | null>(produit.value.couleurs[0]?.nom ?? null)
const taille = ref<string | null>(null)
const variante = computed(() => produit.value?.variantes.find(v =>
  (v.couleur ?? null) === (produit.value!.couleurs.length ? couleur.value : null)
  && (v.taille ?? null) === (produit.value!.tailles.length ? taille.value : null)))
const teinte = computed(() => produit.value?.couleurs.find(c => c.nom === couleur.value)?.hex ?? null)
const tailleDisponible = (t: string) => produit.value!.variantes.some(v => v.taille === t && (!couleur.value || v.couleur === couleur.value))
const prix = computed(() => variante.value?.prix ?? produit.value?.prix_public ?? null)
const remise = computed(() => {
  const avant = produit.value?.prix_avant_promo
  return avant && prix.value ? Math.round((1 - prix.value / avant) * 100) : null
})
const metiersDuProduit = computed(() => (metiers.value ?? []).filter(m => produit.value?.metiers.includes(m.slug)))
const quantite = ref(1)
const personnalisation = ref('')
const ajoute = ref(false)
const erreur = ref('')
const { ajouter } = usePanier()
const adresse = useAdresseImage()
const photo = ref(0)
const photoAbsente = ref(false) // hors ligne, photo pas encore vue : le pictogramme la remplace
watch(photo, () => { photoAbsente.value = false })

function ajouterAuPanier() {
  const p = produit.value!
  if (p.variantes.length && !variante.value) {
    erreur.value = p.tailles.length ? 'Choisissez votre taille.' : 'Choisissez une couleur.'
    return
  }
  ajouter({
    produit_id: p.id,
    variante_id: variante.value?.id ?? null,
    quantite: Math.max(1, Math.min(500, Math.round(quantite.value) || 1)),
    personnalisation: p.personnalisable ? personnalisation.value.trim() || null : null,
    slug: p.slug,
    nom: p.nom,
    variante: variante.value?.libelle ?? null,
    rayon_slug: p.rayon_slug,
    prix_indicatif: prix.value,
  })
  ajoute.value = true
}
watch([couleur, taille, quantite, personnalisation], () => {
  ajoute.value = false
  erreur.value = ''
})
watch(couleur, () => {
  if (taille.value && !tailleDisponible(taille.value)) taille.value = null
})

const lienWhatsapp = computed(() => {
  const p = produit.value!
  const choix = variante.value ? ` (${variante.value.libelle})` : ''
  const objet = p.vendable_en_ligne ? "j'ai une question sur" : 'je souhaite obtenir'
  const texte = `Bonjour, ${objet} : ${p.nom}${choix}. Référence : ${variante.value?.sku ?? p.slug}.`
  return `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent(texte)}`
})
const delai = computed(() => {
  const p = produit.value!
  if (p.fabrique_sur_commande) return `${p.personnalisable ? 'Brodé' : 'Fabriqué'} pour vous à Bamako : comptez ${p.delai_jours} jours. La date exacte vous est donnée à la commande.`
  return `En stock, ou sous ${p.delai_jours} jours. La date exacte vous est donnée dans le panier.`
})

useSeoMeta({
  title: () => produit.value?.nom ?? 'Produit',
  description: () => produit.value?.resume,
  ogTitle: () => produit.value?.nom,
  ogDescription: () => produit.value?.resume,
})

// Données structurées (schema.org) : prix et note moyenne visibles dans les moteurs de recherche.
const origine = useRequestURL().origin
useHead(() => {
  const p = produit.value
  if (!p?.vendable_en_ligne || p.prix_public === null) return {}
  const absolue = (url: string) => (adresse(url).startsWith('http') ? adresse(url) : `${origine}${adresse(url)}`)
  const donnees: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: p.nom,
    description: p.resume,
    sku: p.slug,
    brand: { '@type': 'Brand', name: 'Bibou' },
    image: p.images.map(i => absolue(i.url)),
    offers: { '@type': 'Offer', price: p.prix_public, priceCurrency: 'XOF', availability: 'https://schema.org/InStock' },
  }
  if (p.nombre_avis && p.note_moyenne) {
    donnees.aggregateRating = {
      '@type': 'AggregateRating', ratingValue: p.note_moyenne, reviewCount: p.nombre_avis, bestRating: 5, worstRating: 1,
    }
  }
  // « < » échappé : aucun texte du catalogue ne peut refermer la balise script.
  return { script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(donnees).replace(/</g, '\\u003c') }] }
})
</script>

<template>
  <section v-if="produit" class="conteneur fiche">
    <nav class="fil" aria-label="Fil d'Ariane">
      <NuxtLink to="/">Accueil</NuxtLink> /
      <NuxtLink :to="`/rayons/${produit.rayon_slug}`">{{ produit.rayon_nom }}</NuxtLink>
    </nav>

    <div class="colonnes">
      <div class="visuel">
        <img
          v-if="produit.images[photo] && !photoAbsente" :src="adresse(produit.images[photo]!.url)" :alt="produit.images[photo]!.texte_alternatif"
          @error="photoAbsente = true"
        >
        <ChartePictogramme v-else :type="produit.rayon_slug" :taille="150" :teinte="teinte" />
        <span class="badges">
          <span v-if="produit.est_nouveau" class="badge">Nouveau</span>
          <span v-if="remise" class="badge badge-promo">−{{ remise }} %</span>
        </span>
        <BoutonFavori :slug="produit.slug" :nom="produit.nom" class="bouton-favori" />
        <div v-if="produit.images.length > 1" class="vignettes">
          <button
            v-for="(image, i) in produit.images" :key="image.url" type="button" :class="{ actif: i === photo }"
            :aria-label="`Photo ${i + 1} : ${image.texte_alternatif}`" @click="photo = i"
          >
            <img :src="adresse(image.url)" alt="" width="48" height="60" loading="lazy">
          </button>
        </div>
      </div>

      <div class="infos">
        <p v-if="produit.collection" class="collection">Collection {{ produit.collection }}</p>
        <h1>{{ produit.nom }}</h1>
        <a v-if="produit.nombre_avis && produit.note_moyenne" href="#avis" class="note-resume">
          <NoteEtoiles :note="produit.note_moyenne" />
          {{ formaterNote(produit.note_moyenne) }} ({{ produit.nombre_avis }} avis)
        </a>
        <p class="resume">{{ produit.resume }}</p>

        <template v-if="produit.vendable_en_ligne">
          <p class="prix">
            <ChartePrix :montant="prix" />
            <s v-if="produit.prix_avant_promo" class="barre">{{ formaterFcfa(produit.prix_avant_promo) }}</s>
          </p>
          <p v-if="produit.prix_pro" class="aide">
            Prix professionnel : {{ formaterFcfa(produit.prix_pro) }}, pour les soignants et les structures vérifiés.
          </p>

          <fieldset v-if="produit.couleurs.length > 1 || (produit.couleurs.length && produit.tailles.length === 0)" class="choix">
            <legend>Couleur : <strong>{{ couleur }}</strong></legend>
            <div class="couleurs">
              <label v-for="c in produit.couleurs" :key="c.nom" class="couleur" :class="{ actif: couleur === c.nom }" :title="c.nom">
                <input v-model="couleur" type="radio" name="couleur" :value="c.nom" class="visuellement-cache">
                <span class="teinte" :style="{ background: c.hex ?? '#ccc' }" />
                <span class="visuellement-cache">{{ c.nom }}</span>
              </label>
            </div>
          </fieldset>

          <fieldset v-if="produit.tailles.length" class="choix">
            <legend>
              {{ produit.rayon_slug === 'chaussures' ? 'Pointure' : 'Taille' }}
              <NuxtLink to="/guide-des-tailles" class="guide">Guide des tailles</NuxtLink>
            </legend>
            <div class="tailles">
              <label v-for="t in produit.tailles" :key="t" class="taille" :class="{ actif: taille === t, indisponible: !tailleDisponible(t) }">
                <input v-model="taille" type="radio" name="taille" :value="t" :disabled="!tailleDisponible(t)" class="visuellement-cache">
                {{ t }}
              </label>
            </div>
          </fieldset>

          <div v-if="produit.personnalisable" class="champ">
            <label for="personnalisation">Texte à broder (facultatif)</label>
            <input id="personnalisation" v-model="personnalisation" maxlength="60" placeholder="Aminata Traoré, sage-femme">
            <span class="aide">Nom et fonction. Nous vérifions l'orthographe avec vous avant de broder. <NuxtLink to="/broderie">En savoir plus</NuxtLink></span>
          </div>

          <div class="achat">
            <div class="champ quantite">
              <label for="quantite">Quantité</label>
              <input id="quantite" v-model.number="quantite" type="number" inputmode="numeric" min="1" max="500">
            </div>
            <button type="button" class="bouton" @click="ajouterAuPanier">Ajouter au panier</button>
          </div>
          <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
          <p v-if="ajoute" class="alerte alerte-succes" role="status">
            Ajouté au panier. <NuxtLink to="/panier">Voir le panier</NuxtLink>
          </p>
          <ul class="garanties">
            <li>{{ delai }}</li>
            <li>Paiement à la livraison, en espèces ou par transfert Orange Money ou Moov Money.</li>
            <li>Pour une équipe : <NuxtLink to="/services#structures">demandez un devis</NuxtLink> au prix professionnel.</li>
          </ul>
        </template>

        <div v-else class="alerte alerte-info">
          Cet article relève du domaine pharmaceutique : il est délivré par notre pharmacien
          partenaire. Demandez-le par WhatsApp, nous vous mettons en relation.
        </div>

        <a :href="lienWhatsapp" target="_blank" rel="noopener" :class="produit.vendable_en_ligne ? 'bouton bouton-discret' : 'bouton bouton-large'">
          {{ produit.vendable_en_ligne ? 'Une question ? Écrivez-nous sur WhatsApp' : 'Demander sur WhatsApp' }}
        </a>

        <div class="details">
          <details v-if="produit.description" open>
            <summary>Description</summary>
            <p>{{ produit.description }}</p>
          </details>
          <details v-if="produit.matiere || produit.entretien">
            <summary>Matière et entretien</summary>
            <p v-if="produit.matiere">{{ produit.matiere }}</p>
            <p v-if="produit.entretien">{{ produit.entretien }}</p>
          </details>
          <details v-if="metiersDuProduit.length">
            <summary>Pour quels métiers</summary>
            <p class="metiers">
              <NuxtLink v-for="m in metiersDuProduit" :key="m.slug" :to="`/metiers/${m.slug}`" class="pastille">{{ m.nom }}</NuxtLink>
            </p>
          </details>
        </div>
      </div>
    </div>

    <AvisProduit v-if="produit.vendable_en_ligne && avis" :slug="produit.slug" :page="avis" />

    <section v-if="suggestions.length" class="suggestions">
      <h2>Dans le même rayon</h2>
      <GrilleProduits :produits="suggestions" />
    </section>
  </section>
</template>

<style scoped>
.fiche { padding-top: 20px; }
.fil { margin-bottom: 16px; color: var(--texte-doux); font-size: 0.92rem; }
.fil a { color: inherit; }
.colonnes { display: grid; gap: 28px; grid-template-columns: 1fr; }
@media (min-width: 860px) { .colonnes { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; } }
.visuel { position: relative; display: grid; place-items: center; aspect-ratio: 4 / 5; border-radius: var(--rayon); background: var(--fond-doux); overflow: hidden; }
@media (min-width: 860px) { .visuel { position: sticky; top: 140px; } }
.visuel img { width: 100%; height: 100%; object-fit: cover; }
.badges { position: absolute; top: 14px; left: 14px; display: flex; gap: 6px; }
.bouton-favori { position: absolute; top: 12px; right: 12px; }
.vignettes { position: absolute; bottom: 12px; left: 12px; display: flex; gap: 6px; }
.vignettes button { padding: 0; border: 2px solid transparent; border-radius: 8px; overflow: hidden; background: #fff; cursor: pointer; }
.vignettes button.actif { border-color: var(--primaire); }
.vignettes img { width: 48px; height: 60px; object-fit: cover; }
.badge { padding: 4px 10px; border-radius: 999px; background: var(--primaire); color: #fff; font-size: 0.82rem; font-weight: 750; }
.badge-promo { background: var(--accent); color: var(--texte); }
.collection { margin: 0; color: var(--primaire); font-weight: 700; font-size: 0.92rem; }
.infos h1 { margin: 4px 0 8px; }
.note-resume { display: inline-flex; align-items: center; gap: 8px; color: var(--texte); font-weight: 600; text-decoration: none; margin-bottom: 6px; }
.note-resume:hover { text-decoration: underline; }
.resume { color: var(--texte-doux); font-size: 1.05rem; }
.prix { font-size: 1.6rem; margin: 0 0 4px; display: flex; align-items: baseline; gap: 12px; font-weight: 800; }
.barre { color: var(--texte-doux); font-size: 1.05rem; font-weight: 400; }
.choix { border: 0; padding: 0; margin: 18px 0; }
.choix legend { font-weight: 650; margin-bottom: 8px; display: flex; gap: 12px; align-items: baseline; }
.guide { font-weight: 500; font-size: 0.9rem; }
.couleurs, .tailles { display: flex; flex-wrap: wrap; gap: 8px; }
.couleur { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; cursor: pointer; box-shadow: inset 0 0 0 1.5px var(--bordure); }
.couleur.actif { box-shadow: inset 0 0 0 2.5px var(--primaire); }
.teinte { width: 28px; height: 28px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.taille {
  min-width: 52px; min-height: 44px; padding: 0 12px; display: inline-grid; place-items: center; font-weight: 650;
  border: 1.5px solid var(--bordure); border-radius: 10px; background: var(--surface); cursor: pointer;
}
.taille.actif { border-color: var(--primaire); background: var(--primaire-clair); color: var(--primaire-fonce); }
.taille.indisponible { opacity: 0.4; text-decoration: line-through; cursor: not-allowed; }
.couleur:focus-within, .taille:focus-within { outline: 3px solid var(--accent); outline-offset: 2px; }
.achat { display: flex; align-items: flex-end; gap: 12px; margin: 16px 0 12px; }
.achat .champ { margin: 0; }
.quantite input { width: 92px; }
.achat .bouton { flex: 1; }
.garanties { margin: 12px 0; padding-left: 1.1em; display: grid; gap: 6px; color: var(--texte-doux); font-size: 0.95rem; }
.details { margin-top: 18px; border-top: 1px solid var(--bordure); }
.details details { border-bottom: 1px solid var(--bordure); padding: 4px 0; }
.details summary { padding: 12px 0; font-weight: 750; cursor: pointer; }
.details p { margin: 0 0 12px; }
.metiers { display: flex; flex-wrap: wrap; gap: 6px; }
.metiers a { text-decoration: none; }
.suggestions { margin-top: 40px; }
</style>
