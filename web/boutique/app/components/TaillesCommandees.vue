<script setup lang="ts">
import type { TableauDeBord } from '~/types/tableau'

// Ce qui est commandé, taille par taille et couleur par couleur : l'atelier coupe d'avance,
// l'équipe réassortit. Un petit histogramme par article, à sa propre échelle (on y lit la
// forme de la demande : surtout du M ? du L ?) ; les quantités sont écrites, rien n'est
// laissé à la seule hauteur des barres.
const props = defineProps<{
  produits: TableauDeBord['tailles']
  couleurs: TableauDeBord['couleurs']
}>()

const maxCouleur = computed(() => Math.max(1, ...props.couleurs.map(c => c.quantite)))
function hauteur(quantite: number, tailles: { quantite: number }[]) {
  return `${(quantite / Math.max(1, ...tailles.map(t => t.quantite))) * 100}%`
}
</script>

<template>
  <div class="tailles-couleurs">
    <p v-if="!produits.length && !couleurs.length" class="aide">Aucune commande d'article à tailles ou à couleurs sur la période.</p>
    <div v-if="produits.length" class="multiples">
      <figure v-for="p in produits" :key="p.produit_slug" class="multiple">
        <figcaption>
          <NuxtLink :to="`/produits/${p.produit_slug}`">{{ p.libelle }}</NuxtLink>
          <span class="total">{{ p.quantite }}</span>
        </figcaption>
        <ol class="colonnes-tailles" :aria-label="`Tailles commandées : ${p.libelle}`">
          <li v-for="t in p.tailles" :key="t.taille" :class="{ vide: !t.quantite }">
            <span class="quantite">{{ t.quantite }}</span>
            <span class="piste" aria-hidden="true"><span class="barre" :style="{ height: hauteur(t.quantite, p.tailles) }" /></span>
            <span class="taille"><span class="visuellement-cache">Taille </span>{{ t.taille }}</span>
          </li>
        </ol>
      </figure>
    </div>
    <div v-if="couleurs.length" class="couleurs">
      <h3>Couleurs</h3>
      <ul>
        <li v-for="c in couleurs" :key="c.couleur">
          <span class="pastille-couleur" :style="{ background: c.couleur_hex ?? 'transparent' }" aria-hidden="true" />
          <span class="nom">{{ c.couleur }}</span>
          <span class="piste-h" aria-hidden="true"><span class="barre-h" :style="{ width: `${(c.quantite / maxCouleur) * 100}%` }" /></span>
          <span class="quantite">{{ c.quantite }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.tailles-couleurs { display: grid; gap: 18px; }
.aide { margin: 0; }
.multiples { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); }
/* Titre en haut, histogramme en bas : les lignes de base s'alignent d'une vignette à l'autre. */
.multiple { margin: 0; display: grid; grid-template-rows: auto 1fr; gap: 6px; padding: 10px 12px; border: 1px solid var(--bordure); border-radius: 10px; }
.multiple figcaption { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; font-weight: 650; font-size: 0.95rem; }
.multiple figcaption a { color: inherit; }
.total { color: var(--texte-doux); font-weight: 700; white-space: nowrap; }
.colonnes-tailles { list-style: none; margin: 0; padding: 0; display: flex; gap: 2px; align-items: stretch; align-self: end; height: 118px; }
.colonnes-tailles li { flex: 1 1 0; min-width: 0; display: grid; grid-template-rows: auto 1fr auto; justify-items: center; gap: 2px; }
.colonnes-tailles .quantite { font-size: 0.8rem; font-weight: 700; color: var(--texte); }
.piste { width: 100%; display: flex; justify-content: center; align-items: flex-end; border-bottom: 1px solid var(--grille); }
.barre { width: 100%; max-width: 28px; border-radius: 4px 4px 0 0; background: var(--graphique); }
.vide .quantite { color: var(--texte-doux); font-weight: 500; }
.taille { font-size: 0.78rem; color: var(--texte-doux); white-space: nowrap; }
.couleurs h3 { margin: 0 0 8px; font-size: 1rem; }
.couleurs ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 16px auto minmax(0, 1fr) auto; gap: 6px 8px; }
.couleurs li { grid-column: 1 / -1; display: grid; grid-template-columns: subgrid; align-items: center; font-size: 0.92rem; }
.pastille-couleur { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.25); }
.piste-h { height: 10px; }
.barre-h { display: block; height: 100%; min-width: 2px; border-radius: 0 4px 4px 0; background: var(--graphique); }
.couleurs .quantite { font-weight: 700; text-align: right; min-width: 2ch; }
</style>
