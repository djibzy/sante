<script setup lang="ts">
// Pictogrammes par rayon, en attendant les photos : légers, lisibles par les non-lecteurs.
// « teinte » : la couleur choisie (pastille), pour voir la tenue dans sa couleur sans photo.
const props = defineProps<{ type: string; taille?: number; teinte?: string | null }>()

const BLEU: [string, string] = ['#ecebfd', '#1000d0']
const teintes: Record<string, [string, string]> = {
  'blouses-medicales': BLEU,
  tuniques: BLEU,
  pantalons: BLEU,
  'tenues-de-bloc': ['#e4f4ec', '#177a4a'],
  chaussures: ['#efeefa', '#4b4790'],
  'gilets-polos': BLEU,
  accessoires: ['#efeefa', '#4b4790'],
  kits: ['#e4f4ec', '#177a4a'],
  'materiel-medical': ['#fde8eb', '#b0182e'],
  campagnes: ['#fff1dc', '#b86800'],
}
// Anciens noms de rayons, gardés pour les liens déjà partagés.
const alias: Record<string, string> = {
  'tenues-brodees': 'blouses-medicales',
  'textiles-imprimes': 'campagnes',
  'produits-medicaux': 'materiel-medical',
}
const forme = computed(() => alias[props.type] ?? props.type)
const couleurs = computed(() => teintes[forme.value] ?? ['#f1f1f6', '#5b5a78'])
</script>

<template>
  <svg
    :width="taille ?? 64" :height="taille ?? 64" viewBox="0 0 64 64" aria-hidden="true"
    :fill="teinte ?? 'none'" :stroke="teinte ? '#17153a' : couleurs[1]" :stroke-width="teinte ? 2.2 : 3"
    stroke-linecap="round" stroke-linejoin="round"
  >
    <rect width="64" height="64" rx="16" :fill="couleurs[0]" stroke="none" />
    <g v-if="forme === 'blouses-medicales'">
      <path d="M25 12l-11 6 3 12 5-2v24h20V28l5 2 3-12-11-6-7 9z" />
      <path d="M32 21v31M37 38h4" />
    </g>
    <g v-else-if="forme === 'tuniques' || forme === 'gilets-polos'">
      <path d="M24 14l-10 6 4 9 5-3v24h18V26l5 3 4-9-10-6c-2 4-5 6-8 6s-6-2-8-6z" />
      <path v-if="forme === 'gilets-polos'" d="M32 20v30" />
      <path v-else d="M36 34h5" />
    </g>
    <g v-else-if="forme === 'pantalons'">
      <path d="M21 12h22l3 40h-9l-5-27-5 27h-9z" />
      <path d="M21 18h22" />
    </g>
    <g v-else-if="forme === 'tenues-de-bloc'">
      <path d="M14 34c0-11 8-18 18-18s18 7 18 18z" />
      <path d="M12 34h40M24 40l-4 10M40 40l4 10" />
    </g>
    <g v-else-if="forme === 'chaussures'">
      <path d="M10 40c0-6 4-12 10-14l10-3c3 5 8 8 14 9l6 2c3 1 4 3 4 6v2H10z" />
      <path d="M10 44h44M27 26l3 6M33 25l3 6" />
    </g>
    <g v-else-if="forme === 'kits'">
      <rect x="12" y="22" width="40" height="28" rx="5" />
      <path d="M25 22v-5h14v5M32 29v14M25 36h14" />
    </g>
    <g v-else-if="forme === 'materiel-medical'">
      <path d="M20 14v14a10 10 0 0 0 20 0V14" />
      <path d="M30 38v4a8 8 0 0 0 16 0v-6" />
      <circle cx="46" cy="32" r="4" />
    </g>
    <g v-else-if="forme === 'campagnes'">
      <path d="M14 28v10h8l16 9V19l-16 9z" />
      <path d="M22 38l3 10M44 27a8 8 0 0 1 0 12" />
    </g>
    <g v-else>
      <rect x="18" y="16" width="28" height="36" rx="5" />
      <circle cx="32" cy="30" r="5" />
      <path d="M24 45c2-4 5-6 8-6s6 2 8 6M28 16v-4h8v4" />
    </g>
  </svg>
</template>
