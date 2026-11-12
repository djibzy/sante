<script setup lang="ts">
import type { ProduitResume } from '~/types/catalogue'

const props = defineProps<{ produit: ProduitResume }>()
const adresse = useAdresseImage()
const photoAbsente = ref(false) // hors ligne, photo pas encore vue : le pictogramme la remplace
const remise = computed(() => {
  const { prix_public: prix, prix_avant_promo: avant } = props.produit
  return prix && avant ? Math.round((1 - prix / avant) * 100) : null
})
const delai = computed(() => {
  const p = props.produit
  if (!p.vendable_en_ligne) return 'Par notre pharmacien partenaire'
  if (p.fabrique_sur_commande) return p.personnalisable ? `Brodé pour vous en ${p.delai_jours} jours` : `Fabriqué en ${p.delai_jours} jours`
  return `En stock, ou sous ${p.delai_jours} jours`
})
</script>

<template>
  <article class="carte-produit">
  <NuxtLink :to="`/produits/${produit.slug}`" class="lien">
    <div class="visuel">
      <img v-if="produit.image && !photoAbsente" :src="adresse(produit.image.url)" :alt="produit.image.texte_alternatif" loading="lazy" @error="photoAbsente = true">
      <ChartePictogramme v-else :type="produit.rayon_slug" :taille="96" :teinte="produit.couleurs[0]?.hex" />
      <span class="badges">
        <span v-if="produit.est_nouveau" class="badge">Nouveau</span>
        <span v-if="remise" class="badge badge-promo">−{{ remise }} %</span>
      </span>
    </div>
    <div class="texte">
      <PastillesCouleurs :couleurs="produit.couleurs" />
      <h3>{{ produit.nom }}</h3>
      <p v-if="produit.nombre_avis && produit.note_moyenne" class="note">
        <NoteEtoiles :note="produit.note_moyenne" :taille="14" />
        <span>({{ produit.nombre_avis }}<span class="visuellement-cache"> avis</span>)</span>
      </p>
      <p class="prix">
        <ChartePrix :montant="produit.prix_public" />
        <s v-if="produit.prix_avant_promo" class="barre">{{ formaterFcfa(produit.prix_avant_promo) }}</s>
      </p>
      <p class="delai">{{ delai }}</p>
    </div>
  </NuxtLink>
  <BoutonFavori :slug="produit.slug" :nom="produit.nom" class="bouton-favori" />
  </article>
</template>

<style scoped>
.carte-produit { position: relative; }
.lien { display: flex; flex-direction: column; color: inherit; text-decoration: none; }
.bouton-favori { position: absolute; top: 10px; right: 10px; }
.visuel {
  position: relative; display: grid; place-items: center; aspect-ratio: 4 / 5; border-radius: var(--rayon);
  background: var(--fond-doux); overflow: hidden;
}
.carte-produit:hover .visuel { box-shadow: inset 0 0 0 2px var(--primaire); }
.visuel img { width: 100%; height: 100%; object-fit: cover; }
.badges { position: absolute; top: 10px; left: 10px; display: flex; gap: 6px; }
.badge { padding: 3px 9px; border-radius: 999px; background: var(--primaire); color: #fff; font-size: 0.76rem; font-weight: 750; }
.badge-promo { background: var(--accent); color: var(--texte); }
.texte { padding: 10px 2px 0; display: grid; gap: 4px; }
h3 { font-size: 1rem; font-weight: 650; margin: 0; line-height: 1.3; }
.prix { margin: 0; display: flex; align-items: baseline; gap: 8px; font-weight: 750; }
.barre { color: var(--texte-doux); font-weight: 400; font-size: 0.9rem; }
.delai { margin: 0; color: var(--texte-doux); font-size: 0.85rem; }
.note { margin: 0; display: flex; align-items: center; gap: 6px; color: var(--texte-doux); font-size: 0.85rem; }
</style>
