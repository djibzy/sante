<script setup lang="ts">
import type { TenueProposee } from '~/types/tenues'

// Idée de tenue : le mannequin habillé, les pièces, le total, et l'essai dans le composeur.
const props = defineProps<{ tenue: TenueProposee }>()
const tenue = computed(() => habiller(props.tenue.pieces))
const description = computed(() => `${props.tenue.nom} : ${props.tenue.pieces.map(p => (p.couleur ? `${p.nom} (${p.couleur})` : p.nom)).join(', ')}`)
</script>

<template>
  <article class="carte-tenue">
    <NuxtLink :to="{ path: '/composer', query: tenue.requete }" class="lien">
      <span class="visuel">
        <Mannequin v-bind="tenue.habits" :libelle="description" />
      </span>
      <span class="texte">
        <strong class="nom">{{ props.tenue.nom }}</strong>
        <span v-if="props.tenue.description" class="description">{{ props.tenue.description }}</span>
        <span class="points" aria-hidden="true">
          <span v-for="p in props.tenue.pieces" :key="p.piece" class="point" :style="{ background: p.hex ?? '#f1f0f6' }" />
        </span>
        <span class="bas">
          <span class="total">{{ formaterFcfa(props.tenue.total) }}</span>
          <span class="essayer">Essayer cette tenue</span>
        </span>
      </span>
    </NuxtLink>
  </article>
</template>

<style scoped>
.carte-tenue { flex: none; width: 210px; }
.lien { display: grid; gap: 8px; color: var(--texte); text-decoration: none; }
.visuel {
  display: block; height: 250px; padding: 10px 0; border-radius: 14px;
  background: linear-gradient(var(--fond-doux), var(--surface)); box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.06);
  transition: box-shadow 0.15s;
}
.lien:hover .visuel, .lien:focus-visible .visuel { box-shadow: inset 0 0 0 2px var(--primaire); }
.lien:focus-visible { outline: none; }
.texte { display: grid; gap: 3px; font-size: 0.88rem; line-height: 1.35; }
.nom { font-size: 1rem; }
.description { color: var(--texte-doux); }
.points { display: flex; gap: 4px; margin-top: 2px; }
.point { width: 14px; height: 14px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.bas { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 2px 8px; margin-top: 2px; }
.total { font-weight: 750; white-space: nowrap; }
.essayer { color: var(--primaire); font-weight: 650; }
</style>
