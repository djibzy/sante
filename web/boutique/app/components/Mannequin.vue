<script setup lang="ts">
import type { PieceHabillee } from '~/utils/formes'

// Mannequin de face habillé des pièces choisies (« Composer ma tenue »), chacune dans sa
// couleur : pantalon, haut, blouse ou gilet par-dessus, chaussures, calot.
const props = defineProps<{
  haut?: PieceHabillee | null
  dessus?: PieceHabillee | null
  bas?: PieceHabillee | null
  chaussures?: PieceHabillee | null
  calot?: PieceHabillee | null
  libelle: string
}>()

// Place de chaque forme (cadre 100 × 125) sur le corps (cadre 200 × 400) : épaules, taille.
const POSES: Record<string, string> = {
  tunique: 'translate(21.7 51.1) scale(1.565)',
  polo: 'translate(21.7 52.7) scale(1.565)',
  tshirt: 'translate(21.7 52.7) scale(1.565)',
  blouse: 'translate(25 55.5) scale(1.5)',
  gilet: 'translate(25 55.5) scale(1.5)',
  pantalon: 'translate(25 181) scale(1.5)',
  'pantalon-cargo': 'translate(25 181) scale(1.5)',
  calot: 'translate(64.7 -13.9) scale(.706)',
}
const CORPS = '#dcd9ea'
const TRAIT = '#b3aecb'
const pose = (piece?: PieceHabillee | null) => (piece && POSES[piece.forme] ? piece : null)
const souliers = computed(() => {
  const hex = props.chaussures?.hex
  if (!hex) return null
  return {
    hex,
    contour: estClaire(hex) ? '#a19fbc' : melanger(hex, '#0b0a1f', 0.45),
    semelle: luminance(hex) < 0.2 ? '#f1f0f7' : '#cfcde0',
  }
})
</script>

<template>
  <svg viewBox="0 0 200 400" class="mannequin" role="img" :aria-label="libelle">
    <g :fill="CORPS" :stroke="TRAIT" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
      <!-- Bras et jambes derrière les vêtements, puis le buste. -->
      <path d="M70 92Q58 150 54 226M130 92Q142 150 146 226" fill="none" :stroke="CORPS" stroke-width="13" />
      <circle cx="54" cy="230" r="7" />
      <circle cx="146" cy="230" r="7" />
      <path d="M80 196L76 352M120 196L124 352" fill="none" :stroke="CORPS" stroke-width="22" />
      <path d="M66 86Q100 76 134 86L130 202Q100 210 70 202Z" />
      <path d="M92 58h16v22h-16Z" />
      <circle cx="100" cy="42" r="21" />
      <ellipse v-if="!souliers" cx="76" cy="362" rx="13" ry="7" />
      <ellipse v-if="!souliers" cx="124" cy="362" rx="13" ry="7" />
    </g>
    <TraceVetement v-if="pose(bas)" v-bind="bas!" :transform="POSES[bas!.forme]" />
    <TraceVetement v-if="pose(haut)" v-bind="haut!" :transform="POSES[haut!.forme]" />
    <TraceVetement v-if="pose(dessus)" v-bind="dessus!" :transform="POSES[dessus!.forme]" ouvert />
    <g v-if="souliers" :fill="souliers.hex" :stroke="souliers.contour" stroke-width="1.2" stroke-linejoin="round">
      <path d="M62 356Q62 349 70 349L86 349Q93 349 93 357L94 370Q94 375 88 375L66 375Q60 375 61 369Z" />
      <path d="M138 356Q138 349 130 349L114 349Q107 349 107 357L106 370Q106 375 112 375L134 375Q140 375 139 369Z" />
      <path d="M61 370h33v3q0 3-3 3h-27q-3 0-3-3ZM106 370h33v3q0 3-3 3h-27q-3 0-3-3Z" :fill="souliers.semelle" />
    </g>
    <TraceVetement v-if="pose(calot)" v-bind="calot!" :transform="POSES[calot!.forme]" />
  </svg>
</template>

<style scoped>
.mannequin { display: block; width: 100%; height: 100%; }
</style>
