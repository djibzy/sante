<script setup lang="ts">
import type { ProduitResume } from '~/types/catalogue'

defineProps<{ produit: ProduitResume }>()
</script>

<template>
  <NuxtLink :to="`/produits/${produit.slug}`" class="carte carte-produit">
    <div class="visuel">
      <img v-if="produit.image" :src="produit.image.url" :alt="produit.image.texte_alternatif" loading="lazy">
      <ChartePictogramme v-else :type="produit.rayon_slug" :taille="88" />
    </div>
    <div class="texte">
      <span v-if="produit.personnalisable" class="pastille">Personnalisable</span>
      <span v-if="!produit.vendable_en_ligne" class="pastille pastille-accent">Pharmacien partenaire</span>
      <h3>{{ produit.nom }}</h3>
      <p>{{ produit.resume }}</p>
      <ChartePrix :montant="produit.prix_public" />
    </div>
  </NuxtLink>
</template>

<style scoped>
.carte-produit { display: flex; flex-direction: column; overflow: hidden; color: inherit; text-decoration: none; transition: transform 0.15s; }
.carte-produit:hover { transform: translateY(-2px); }
.visuel { display: grid; place-items: center; aspect-ratio: 4 / 3; background: var(--fond); }
.visuel img { width: 100%; height: 100%; object-fit: cover; }
.texte { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.texte .pastille { align-self: flex-start; }
h3 { font-size: 1.02rem; margin: 2px 0 0; }
p { color: var(--texte-doux); font-size: 0.9rem; margin: 0; flex: 1; }
</style>
