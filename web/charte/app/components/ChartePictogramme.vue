<script setup lang="ts">
// Pictogrammes par rayon, en attendant les photos : légers, lisibles par les non-lecteurs.
const props = defineProps<{ type: string; taille?: number }>()

const teintes: Record<string, [string, string]> = {
  'tenues-brodees': ['#e3f1ea', '#0f6b4a'],
  'textiles-imprimes': ['#fbeee2', '#b25a14'],
  kits: ['#e8eefb', '#2c56a8'],
  'produits-medicaux': ['#fdecea', '#b42318'],
  accessoires: ['#f1ecf8', '#6b4aa0'],
}
const couleurs = computed(() => teintes[props.type] ?? ['#eeeae2', '#5a6a62'])
</script>

<template>
  <svg
    :width="taille ?? 64" :height="taille ?? 64" viewBox="0 0 64 64" aria-hidden="true"
    fill="none" :stroke="couleurs[1]" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
  >
    <rect width="64" height="64" rx="16" :fill="couleurs[0]" stroke="none" />
    <g v-if="type === 'tenues-brodees'">
      <path d="M24 14l-10 6 4 9 5-3v24h18V26l5 3 4-9-10-6c-2 4-5 6-8 6s-6-2-8-6z" />
      <path d="M36 34h5" />
    </g>
    <g v-else-if="type === 'textiles-imprimes'">
      <path d="M22 14l-9 7 4 7 5-3v25h20V25l5 3 4-7-9-7c-1 3-4 5-10 5s-9-2-10-5z" />
      <path d="M27 34h10M29 40h6" />
    </g>
    <g v-else-if="type === 'kits'">
      <rect x="12" y="22" width="40" height="28" rx="5" />
      <path d="M25 22v-5h14v5M32 29v14M25 36h14" />
    </g>
    <g v-else-if="type === 'produits-medicaux'">
      <path d="M20 14v14a10 10 0 0 0 20 0V14" />
      <path d="M30 38v4a8 8 0 0 0 16 0v-6" />
      <circle cx="46" cy="32" r="4" />
    </g>
    <g v-else>
      <rect x="18" y="16" width="28" height="36" rx="5" />
      <circle cx="32" cy="30" r="5" />
      <path d="M24 45c2-4 5-6 8-6s6 2 8 6M28 16v-4h8v4" />
    </g>
  </svg>
</template>
