<script setup lang="ts">
import type { ArticleOffre, Formule, Partenaire } from '~/types/prestations'

// Avant de signer : ce que le contrat rapporterait par mois avec les volumes annoncés, ce que
// coûterait le partenaire choisi, et la marge. Une estimation pour fixer les prix, rien de plus.
const props = defineProps<{
  articles: ArticleOffre[]
  formule: Formule
  tarifs: Record<string, number | null>
  forfait: number | null
  piecesIncluses: number | null
  prixSupplement: number | null
  partenaire?: Partenaire
}>()
const volumes = defineModel<Record<string, number | null>>({ required: true })
const SEMAINES_PAR_MOIS = 52 / 12

const calcul = computed(() => {
  const lignes = Object.entries(volumes.value)
    .filter(([, n]) => (n ?? 0) > 0)
    .map(([article, n]) => ({ article, pieces: Math.round((n ?? 0) * SEMAINES_PAR_MOIS) }))
  const pieces = lignes.reduce((total, l) => total + l.pieces, 0)
  const sansPrix = lignes.filter(l => props.formule === 'piece' && props.tarifs[l.article] == null).map(l => l.article)
  const montant = props.formule === 'forfait'
    ? (props.forfait ?? 0) + Math.max(0, pieces - (props.piecesIncluses ?? pieces)) * (props.prixSupplement ?? 0)
    : lignes.reduce((total, l) => total + l.pieces * (props.tarifs[l.article] ?? 0), 0)
  const auKilo = props.partenaire?.mode_tarif === 'kg'
  const sansCout = props.partenaire && !auKilo
    ? lignes.filter(l => props.partenaire!.tarifs[l.article] == null).map(l => l.article)
    : []
  const cout = props.partenaire && !auKilo
    ? lignes.reduce((total, l) => total + l.pieces * (props.partenaire!.tarifs[l.article] ?? 0), 0)
    : null
  return { pieces, montant, cout, auKilo, sansPrix, sansCout }
})
const nom = (code: string) => props.articles.find(a => a.code === code)?.pluriel ?? code
const marge = computed(() => (calcul.value.cout === null ? null : calcul.value.montant - calcul.value.cout))
</script>

<template>
  <details class="estimation" :open="Object.values(volumes).some(n => (n ?? 0) > 0)">
    <summary>Estimer le mois <span class="aide">(volumes annoncés, prix ci-dessus, partenaire choisi)</span></summary>
    <p class="aide">Pièces par semaine : celles de la demande, à corriger après la visite.</p>
    <GrilleArticles v-model="volumes" :articles="articles.filter(a => a.code !== 'autre')" identifiant="estimation" :avec-precision="false" />
    <dl v-if="calcul.pieces" class="resultat" aria-live="polite">
      <div><dt>Pièces par mois</dt><dd>{{ calcul.pieces }}</dd></div>
      <div><dt>Montant par mois</dt><dd>{{ formaterFcfa(calcul.montant) }}</dd></div>
      <div>
        <dt>Coût du partenaire</dt>
        <dd>{{ calcul.cout === null ? (calcul.auKilo ? 'au kilo : après une pesée' : 'choisir un partenaire') : formaterFcfa(calcul.cout) }}</dd>
      </div>
      <div v-if="marge !== null">
        <dt>Marge</dt>
        <dd :class="{ negative: marge < 0 }">
          {{ formaterFcfa(marge) }}<template v-if="calcul.montant"> ({{ Math.round((marge / calcul.montant) * 100) }} %)</template>
        </dd>
      </div>
    </dl>
    <p v-if="calcul.sansPrix.length" class="alerte alerte-erreur">Sans prix au contrat : {{ calcul.sansPrix.map(nom).join(', ') }}.</p>
    <p v-if="calcul.sansCout.length" class="aide">Sans tarif chez le partenaire : {{ calcul.sansCout.map(nom).join(', ') }} (coût sous-estimé).</p>
  </details>
</template>

<style scoped>
.estimation { border: 1px dashed var(--bordure); border-radius: 12px; padding: 10px 14px; }
.estimation summary { cursor: pointer; font-weight: 700; }
.resultat { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 160px), 1fr)); margin: 14px 0 8px; }
.resultat dt { color: var(--texte-doux); font-size: 0.85rem; }
.resultat dd { margin: 0; font-weight: 800; font-size: 1.1rem; font-variant-numeric: tabular-nums; }
.negative { color: var(--danger); }
</style>
