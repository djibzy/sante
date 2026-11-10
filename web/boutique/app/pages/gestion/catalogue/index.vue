<script setup lang="ts">
import type { ProduitGestion, RayonGestion } from '~/types/gestion'

useSeoMeta({ title: 'Catalogue', robots: 'noindex' })
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const produits = ref<ProduitGestion[]>([])
const rayons = ref<RayonGestion[]>([])
const recherche = ref('')
const rayon = ref('')
const erreur = ref('')

async function charger() {
  if (!autorise.value) return
  try {
    const [p, r] = await Promise.all([
      appeler<ProduitGestion[]>('/api/v1/admin/produits', { query: { q: recherche.value || undefined, rayon: rayon.value || undefined } }),
      appeler<RayonGestion[]>('/api/v1/admin/rayons'),
    ])
    produits.value = p
    rayons.value = r
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

watch([verifie, rayon], charger)
</script>

<template>
  <section class="conteneur catalogue">
    <AccesEquipe>
      <div class="entete-catalogue">
        <h1>Catalogue</h1>
        <NuxtLink to="/gestion/catalogue/nouveau" class="bouton">Nouveau produit</NuxtLink>
      </div>
      <form class="outils" role="search" @submit.prevent="charger">
        <label class="visuellement-cache" for="recherche-catalogue">Nom du produit</label>
        <input id="recherche-catalogue" v-model="recherche" type="search" placeholder="Nom du produit">
        <label class="visuellement-cache" for="rayon-catalogue">Rayon</label>
        <select id="rayon-catalogue" v-model="rayon">
          <option value="">Tous les rayons</option>
          <option v-for="r in rayons" :key="r.slug" :value="r.slug">{{ r.nom }}</option>
        </select>
        <button type="submit" class="bouton bouton-secondaire">Chercher</button>
      </form>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <table v-if="produits.length" class="carte tableau">
        <thead>
          <tr><th scope="col">Produit</th><th scope="col">Rayon</th><th scope="col">Prix</th><th scope="col">Variantes</th><th scope="col">État</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in produits" :key="p.id" :class="{ inactif: !p.est_actif }">
            <th scope="row"><NuxtLink :to="`/gestion/catalogue/${p.id}`">{{ p.nom }}</NuxtLink><small>{{ p.slug }}</small></th>
            <td>{{ p.rayon_nom }}</td>
            <td>
              <template v-if="p.categorie_reglementaire === 'pharmaceutique'">Pharmacien</template>
              <template v-else>{{ p.prix_public !== null ? formaterFcfa(p.prix_public) : '' }}<small v-if="p.prix_avant_promo">au lieu de {{ formaterFcfa(p.prix_avant_promo) }}</small></template>
            </td>
            <td>{{ p.variantes.filter(v => v.est_active).length }}</td>
            <td>
              <span v-if="!p.est_actif" class="pastille pastille-danger">Retiré</span>
              <span v-else-if="p.est_nouveau" class="pastille">Nouveau</span>
              <span v-else class="pastille pastille-succes">En ligne</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="verifie" class="aide">Aucun produit.</p>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.catalogue { padding-top: 20px; }
.entete-catalogue { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.entete-catalogue h1 { margin: 0; }
.outils { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
.outils input, .outils select { min-height: 44px; padding: 0 10px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; background: var(--surface); }
.outils input { flex: 1; min-width: 180px; }
.tableau { width: 100%; border-collapse: collapse; overflow: hidden; }
.tableau th, .tableau td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--bordure); vertical-align: top; }
.tableau thead th { font-size: 0.85rem; color: var(--texte-doux); }
.tableau small { display: block; color: var(--texte-doux); font-weight: 400; font-size: 0.8rem; }
.tableau tr.inactif th a { color: var(--texte-doux); }
@media (max-width: 700px) { .tableau thead { display: none; } .tableau tr { display: grid; grid-template-columns: 1fr auto; } .tableau td:nth-child(2), .tableau td:nth-child(4) { display: none; } }
</style>
