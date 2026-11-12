<script setup lang="ts">
import { formaterNote } from '~/types/avis'

// Cinq étoiles remplies selon la note (demi-étoiles comprises) ; la note est lue en texte.
const props = withDefaults(defineProps<{ note: number, taille?: number }>(), { taille: 16 })
const largeur = computed(() => `${(Math.max(0, Math.min(5, props.note)) / 5) * 100}%`)
const ETOILE = 'M12 2.6l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.5l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z'
</script>

<template>
  <span class="etoiles" role="img" :aria-label="`Note : ${formaterNote(note)} sur 5`" :style="{ height: `${taille}px`, width: `${taille * 5}px` }">
    <svg class="rangee vide" :viewBox="`0 0 120 24`" aria-hidden="true" focusable="false">
      <path v-for="i in 5" :key="i" :d="ETOILE" :transform="`translate(${(i - 1) * 24} 0)`" />
    </svg>
    <span class="remplies" :style="{ width: largeur }">
      <svg class="rangee pleine" :viewBox="`0 0 120 24`" :style="{ width: `${taille * 5}px` }" aria-hidden="true" focusable="false">
        <path v-for="i in 5" :key="i" :d="ETOILE" :transform="`translate(${(i - 1) * 24} 0)`" />
      </svg>
    </span>
  </span>
</template>

<style scoped>
.etoiles { position: relative; display: inline-block; flex-shrink: 0; vertical-align: -0.15em; }
/* max-width : la règle commune des images réduirait la rangée pleine à la largeur remplie. */
.rangee { display: block; height: 100%; width: 100%; max-width: none; }
.vide { fill: var(--etoile-vide); }
.remplies { position: absolute; inset: 0 auto 0 0; overflow: hidden; }
.pleine { fill: var(--etoile); height: 100%; }
</style>
