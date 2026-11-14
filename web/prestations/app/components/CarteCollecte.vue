<script setup lang="ts">
import type { Collecte } from '~/types/prestations'
import { classeCollecte } from '~/types/prestations'

defineProps<{ collecte: Collecte }>()
</script>

<template>
  <article class="carte carte-collecte">
    <header>
      <NuxtLink :to="`/equipe/collectes/${collecte.reference}`" class="reference">{{ collecte.reference }}</NuxtLink>
      <span :class="classeCollecte(collecte.statut, collecte.en_retard)">{{ collecte.en_retard ? 'En retard' : collecte.libelle_statut }}</span>
    </header>
    <p class="structure"><strong>{{ collecte.contrat.structure }}</strong></p>
    <p class="aide">
      {{ collecte.pieces_enlevees }} pièce{{ collecte.pieces_enlevees > 1 ? 's' : '' }} enlevée{{ collecte.pieces_enlevees > 1 ? 's' : '' }} le {{ jourCourt(collecte.prevue_le) }}
      <template v-if="collecte.retour_prevu_le"> · retour promis {{ jourCourt(collecte.retour_prevu_le) }}</template>
      <template v-if="collecte.partenaire"> · {{ collecte.partenaire.nom }}</template>
    </p>
    <slot />
  </article>
</template>

<style scoped>
.carte-collecte { padding: 14px 16px; display: grid; gap: 4px; }
.carte-collecte header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.reference { font-weight: 800; }
.carte-collecte p { margin: 0; }
</style>
