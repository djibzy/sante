<script setup lang="ts">
import type { Trace } from '~/utils/formes'

// Un vêtement dessiné (groupe SVG) : dans une illustration seule, ou posé sur le mannequin
// avec `transform`. Ses dégradés et motifs ont des identifiants propres.
const props = defineProps<{
  forme: string
  hex: string
  couleur?: string | null
  brode?: boolean
  transform?: string
  ouvert?: boolean // porté ouvert par-dessus : l'encolure laisse voir le haut
}>()

const id = useId()
const traces = computed(() => (FORMES[props.forme] ?? []).filter(t => !(props.ouvert && t.remplissage === 'col')))
const claire = computed(() => estClaire(props.hex))
const wax = computed(() => (props.couleur ?? '').toLowerCase().startsWith('wax'))
const teintes = computed(() => {
  const base = props.hex
  const sombre = '#0b0a1f'
  return {
    base,
    ombre: claire.value ? '#e2e0ee' : melanger(base, sombre, 0.22),
    clair: melanger(base, '#ffffff', 0.32),
    col: claire.value ? '#d3d7e7' : melanger(base, sombre, 0.38),
    semelle: luminance(base) < 0.2 ? '#f1f0f7' : '#cfcde0',
    cadran: '#ffffff',
    aucun: 'none',
    contour: claire.value ? '#a19fbc' : melanger(base, sombre, 0.45),
    detail: claire.value ? '#bdbbd3' : melanger(base, sombre, 0.3),
    fil: claire.value ? '#1000d0' : '#f4f3fb',
    // Motif wax : la couleur du tissu, des ronds clairs et une couleur opposée en accent.
    accent: Number.parseInt(base.slice(5, 7), 16) > Number.parseInt(base.slice(1, 3), 16) ? '#f2b33d' : '#1c3f8f',
  }
})
const remplir = (t: Trace) => teintes.value[t.remplissage ?? 'aucun']
const tracer = (t: Trace) => (t.trait === 'aucun' ? 'none' : teintes.value[t.trait ?? 'detail'])
</script>

<template>
  <g :transform="transform" stroke-linecap="round" stroke-linejoin="round">
    <defs>
      <linearGradient :id="`${id}-modele`" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0" stop-color="#fff" stop-opacity=".18" />
        <stop offset=".45" stop-color="#fff" stop-opacity="0" />
        <stop offset="1" stop-color="#000" stop-opacity=".13" />
      </linearGradient>
      <pattern v-if="wax" :id="`${id}-wax`" width="13" height="13" patternUnits="userSpaceOnUse" patternTransform="rotate(28)">
        <circle cx="6.5" cy="6.5" r="4.6" :fill="teintes.clair" />
        <circle cx="6.5" cy="6.5" r="2.4" :fill="teintes.accent" />
        <circle cx="0" cy="0" r="1.5" :fill="teintes.col" />
        <circle cx="13" cy="13" r="1.5" :fill="teintes.col" />
      </pattern>
    </defs>
    <g v-for="(t, i) in traces" :key="i" :transform="t.transform">
      <path
        :d="t.d" :fill="remplir(t)" :stroke="tracer(t)" :stroke-width="t.epaisseur ?? 1.2"
        :stroke-dasharray="t.pointille ? '2 2.4' : undefined" vector-effect="non-scaling-stroke"
      />
      <template v-if="t.corps">
        <path v-if="wax" :d="t.d" :fill="`url(#${id}-wax)`" stroke="none" />
        <path :d="t.d" :fill="`url(#${id}-modele)`" stroke="none" />
      </template>
    </g>
    <path
      v-if="brode && BRODERIES[forme]" :d="BRODERIES[forme]" :stroke="teintes.fil" stroke-width="1.6"
      stroke-dasharray="1.4 1.1" fill="none" vector-effect="non-scaling-stroke"
    />
  </g>
</template>
