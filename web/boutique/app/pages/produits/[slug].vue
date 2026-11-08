<script setup lang="ts">
import type { ProduitDetail } from '~/types/catalogue'

const route = useRoute()
const config = useRuntimeConfig()
const { data: produit } = await useBoutiqueFetch<ProduitDetail>(
  () => `/api/v1/produits/${String(route.params.slug)}`,
)
if (!produit.value) {
  throw createError({ statusCode: 404, statusMessage: 'Produit introuvable', fatal: true })
}

const varianteId = ref(produit.value.variantes[0]?.id ?? null)
const variante = computed(() => produit.value?.variantes.find(v => v.id === varianteId.value))
const prix = computed(() => variante.value?.prix ?? produit.value?.prix_public ?? null)
const quantite = ref(1)
const personnalisation = ref('')
const ajoute = ref(false)
const { ajouter } = usePanier()

function ajouterAuPanier() {
  const p = produit.value!
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
watch([varianteId, quantite, personnalisation], () => { ajoute.value = false })

const lienWhatsapp = computed(() => {
  const p = produit.value!
  const choix = variante.value ? ` (${variante.value.libelle})` : ''
  const objet = p.vendable_en_ligne ? "j'ai une question sur" : 'je souhaite obtenir'
  const texte = `Bonjour, ${objet} : ${p.nom}${choix}. Référence : ${variante.value?.sku ?? p.slug}.`
  return `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent(texte)}`
})

useSeoMeta({
  title: () => produit.value?.nom ?? 'Produit',
  description: () => produit.value?.resume,
  ogTitle: () => produit.value?.nom,
  ogDescription: () => produit.value?.resume,
})
</script>

<template>
  <section v-if="produit" class="conteneur fiche">
    <nav class="fil" aria-label="Fil d'Ariane">
      <NuxtLink to="/">Accueil</NuxtLink> ›
      <NuxtLink :to="`/rayons/${produit.rayon_slug}`">{{ produit.rayon_nom }}</NuxtLink>
    </nav>

    <div class="colonnes">
      <div class="carte visuel">
        <img v-if="produit.images[0]" :src="produit.images[0].url" :alt="produit.images[0].texte_alternatif">
        <ChartePictogramme v-else :type="produit.rayon_slug" :taille="140" />
      </div>

      <div class="infos">
        <span v-if="produit.personnalisable" class="pastille">Personnalisable</span>
        <h1>{{ produit.nom }}</h1>
        <p class="resume">{{ produit.resume }}</p>

        <template v-if="produit.vendable_en_ligne">
          <p class="prix"><ChartePrix :montant="prix" /></p>
          <p v-if="produit.prix_pro" class="aide">
            Prix professionnel : {{ formaterFcfa(produit.prix_pro) }} pour les structures et les soignants.
          </p>

          <fieldset v-if="produit.variantes.length" class="variantes">
            <legend>Choisir</legend>
            <label v-for="v in produit.variantes" :key="v.id" :class="{ actif: v.id === varianteId }">
              <input v-model="varianteId" type="radio" name="variante" :value="v.id" class="visuellement-cache">
              {{ v.taille ?? v.libelle }}
            </label>
          </fieldset>

          <div v-if="produit.personnalisable" class="champ">
            <label for="personnalisation">Texte à broder ou à imprimer (facultatif)</label>
            <input id="personnalisation" v-model="personnalisation" maxlength="200" placeholder="Aminata Traoré, sage-femme">
            <span class="aide">
              Nom, fonction ou nom de votre structure. Nous vous montrons un aperçu avant la
              fabrication. Délai indicatif : {{ produit.delai_jours }} jours.
            </span>
          </div>

          <div class="achat">
            <div class="champ quantite">
              <label for="quantite">Quantité</label>
              <input id="quantite" v-model.number="quantite" type="number" inputmode="numeric" min="1" max="500">
            </div>
            <button type="button" class="bouton" @click="ajouterAuPanier">Ajouter au panier</button>
          </div>
          <p v-if="ajoute" class="alerte alerte-succes" role="status">
            Ajouté au panier. <NuxtLink to="/panier">Voir le panier</NuxtLink>
          </p>
          <p class="aide">
            Paiement à la livraison, en espèces ou par transfert Orange Money ou Moov Money.
          </p>
        </template>

        <div v-else class="alerte alerte-info">
          Cet article relève du domaine pharmaceutique : il est délivré par notre pharmacien
          partenaire. Demandez-le par WhatsApp, nous vous mettons en relation.
        </div>

        <a
          :href="lienWhatsapp" target="_blank" rel="noopener"
          :class="produit.vendable_en_ligne ? 'bouton bouton-secondaire bouton-large' : 'bouton bouton-large'"
        >
          {{ produit.vendable_en_ligne ? 'Poser une question sur WhatsApp' : 'Demander sur WhatsApp' }}
        </a>

        <div v-if="produit.description" class="description">
          <h2>Description</h2>
          <p>{{ produit.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.fiche { padding-top: 20px; }
.fil { margin-bottom: 16px; color: var(--texte-doux); font-size: 0.92rem; }
.fil a { text-decoration: none; }
.colonnes { display: grid; gap: 24px; grid-template-columns: 1fr; }
@media (min-width: 820px) { .colonnes { grid-template-columns: 1fr 1fr; align-items: start; } }
.visuel { display: grid; place-items: center; aspect-ratio: 4 / 3; overflow: hidden; }
@media (min-width: 820px) { .visuel { aspect-ratio: 1; } }
.visuel img { width: 100%; height: 100%; object-fit: cover; }
.infos h1 { margin-top: 8px; }
.resume { color: var(--texte-doux); font-size: 1.05rem; }
.prix { font-size: 1.6rem; margin: 0 0 4px; }
.variantes { border: 0; padding: 0; margin: 20px 0; display: flex; flex-wrap: wrap; gap: 8px; }
.variantes legend { font-weight: 600; margin-bottom: 8px; }
.variantes label {
  min-width: 52px; min-height: 44px; padding: 0 14px; display: inline-grid; place-items: center;
  border: 1.5px solid var(--bordure); border-radius: 10px; background: var(--surface); cursor: pointer;
}
.variantes label.actif { border-color: var(--primaire); background: var(--primaire-clair); font-weight: 700; }
.description { margin-top: 24px; }
.achat { display: flex; align-items: flex-end; gap: 12px; margin-bottom: 12px; }
.achat .champ { margin: 0; }
.quantite input { width: 92px; }
.achat .bouton { flex: 1; }
</style>
