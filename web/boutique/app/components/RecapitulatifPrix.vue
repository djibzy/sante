<script setup lang="ts">
import type { Chiffrage } from '~/types/commandes'

defineProps<{ chiffrage: Chiffrage | null; enCours?: boolean }>()
const { livraison } = usePanier()
</script>

<template>
  <dl v-if="chiffrage" class="recap" :class="{ attente: enCours }" aria-live="polite">
    <div><dt>Articles</dt><dd>{{ formaterFcfa(chiffrage.sous_total) }}</dd></div>
    <div>
      <dt>Livraison</dt>
      <dd>{{ chiffrage.frais_livraison ? formaterFcfa(chiffrage.frais_livraison) : 'Gratuit' }}</dd>
    </div>
    <div v-if="chiffrage.remise" class="remise">
      <dt>Réduction {{ chiffrage.code_promo }}</dt><dd>− {{ formaterFcfa(chiffrage.remise) }}</dd>
    </div>
    <div class="total">
      <dt>{{ chiffrage.acompte ? 'Total' : 'Total à payer à la livraison' }}</dt><dd>{{ formaterFcfa(chiffrage.total) }}</dd>
    </div>
    <template v-if="chiffrage.acompte">
      <div class="acompte">
        <dt>Acompte à la confirmation <small>non remboursable</small></dt><dd>{{ formaterFcfa(chiffrage.acompte) }}</dd>
      </div>
      <div><dt>Reste à la livraison</dt><dd>{{ formaterFcfa(chiffrage.total - chiffrage.acompte) }}</dd></div>
    </template>
    <p class="aide">
      {{ livraison.mode === 'livraison' ? 'Livraison prévue vers le' : 'Prêt à retirer vers le' }}
      {{ formaterDate(chiffrage.date_estimee) }}, confirmé par téléphone{{ chiffrage.acompte ? ", si l'acompte est réglé dès notre appel" : '' }}.
    </p>
  </dl>
</template>

<style scoped>
.recap { margin: 0; display: grid; gap: 6px; transition: opacity 0.2s; }
.recap.attente { opacity: 0.55; }
.recap div { display: flex; justify-content: space-between; gap: 12px; }
.recap dt { color: var(--texte-doux); }
.recap dd { margin: 0; font-weight: 650; white-space: nowrap; }
.recap .remise dd { color: var(--succes); }
.recap .total { padding-top: 8px; margin-top: 4px; border-top: 1px solid var(--bordure); }
.recap .total dt { color: var(--texte); font-weight: 700; }
.recap .total dd { font-size: 1.25rem; font-weight: 800; color: var(--primaire); }
.recap .acompte dt { color: var(--texte); font-weight: 650; }
.recap .acompte small { display: block; color: var(--texte-doux); font-weight: 400; }
.recap .aide { margin: 4px 0 0; }
</style>
