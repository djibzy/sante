<script setup lang="ts">
import type { Evenement } from '~/types/commandes'

defineProps<{ evenements: (Evenement & { visible_client?: boolean })[] }>()
</script>

<template>
  <ol class="historique">
    <li v-for="(e, i) in evenements" :key="i" :class="{ dernier: i === evenements.length - 1, interne: e.visible_client === false }">
      <strong>{{ e.libelle }}</strong>
      <time :datetime="e.cree_le">{{ formaterDateHeure(e.cree_le) }}</time>
      <span v-if="e.note" class="note">{{ e.note }}<em v-if="e.visible_client === false"> (note interne)</em></span>
    </li>
  </ol>
</template>

<style scoped>
.historique { list-style: none; margin: 0; padding: 0; }
.historique li { position: relative; padding: 0 0 16px 26px; display: grid; gap: 1px; }
.historique li::before {
  content: ''; position: absolute; left: 5px; top: 6px; width: 12px; height: 12px; border-radius: 50%;
  background: var(--surface); border: 2px solid var(--primaire);
}
.historique li:not(:last-child)::after {
  content: ''; position: absolute; left: 10px; top: 20px; bottom: 0; width: 2px; background: var(--bordure);
}
.historique li.dernier::before { background: var(--accent); border-color: var(--accent); }
.historique li.interne strong { color: var(--texte-doux); }
time { color: var(--texte-doux); font-size: 0.88rem; }
.note { font-size: 0.95rem; }
</style>
