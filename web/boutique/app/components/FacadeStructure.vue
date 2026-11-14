<script setup lang="ts">
// Façade d'un centre de santé peinte aux couleurs de la structure : murs, soubassement,
// bandeau du toit, porte, et l'enseigne avec le logo. Une esquisse pour se projeter, pas un
// plan : les teintes exactes se choisissent sur un nuancier.
const props = defineProps<{
  mur: string
  soubassement: string
  porte: string
  bandeau: string
  logo?: string | null
  nom?: string
  libelle: string
}>()

const ENCRE = '#1d1b3a'
const texteEnseigne = computed(() => (estClaire(props.soubassement) ? ENCRE : props.soubassement))
const cadre = computed(() => melanger(props.soubassement, '#000000', 0.15))
// Le nom sur l'enseigne : une ligne s'il est court, sinon deux, police réduite au besoin.
const enseigne = computed(() => {
  const nom = (props.nom ?? '').trim() || 'Votre structure'
  const place = props.logo ? 100 : 134 // largeur utile du panneau, en unités du dessin
  const taille = (lignes: string[]) => Math.min(13, place / (0.56 * Math.max(...lignes.map(l => l.length))))
  if (taille([nom]) >= 11) return { lignes: [nom], taille: taille([nom]) }
  const mots = nom.split(/\s+/)
  let coupure = 1
  let meilleur = Infinity
  for (let i = 1; i < mots.length; i++) {
    const ecartLongueurs = Math.abs(mots.slice(0, i).join(' ').length - mots.slice(i).join(' ').length)
    if (ecartLongueurs < meilleur) [meilleur, coupure] = [ecartLongueurs, i]
  }
  let lignes = mots.length > 1 ? [mots.slice(0, coupure).join(' '), mots.slice(coupure).join(' ')] : [nom]
  const max = Math.floor(place / (0.56 * 8.5))
  lignes = lignes.map(l => (l.length > max ? `${l.slice(0, max - 1)}…` : l))
  return { lignes, taille: Math.max(8.5, taille(lignes)) }
})
const FENETRES = [36, 84, 212, 260]
</script>

<template>
  <svg viewBox="0 0 320 210" class="facade" role="img" :aria-label="libelle">
    <rect x="0" y="194" width="320" height="16" fill="#d9cdb7" />
    <rect x="22" y="44" width="276" height="152" :fill="mur" stroke="#00000022" />
    <rect x="14" y="34" width="292" height="14" rx="2" :fill="bandeau" />
    <rect x="22" y="160" width="276" height="36" :fill="soubassement" />
    <g v-for="x in FENETRES" :key="x">
      <rect :x="x" y="96" width="30" height="40" rx="2" fill="#cfe3ee" :stroke="cadre" stroke-width="3" />
      <path :d="`M${x + 15} 96v40M${x} 116h30`" :stroke="cadre" stroke-width="2" />
    </g>
    <rect x="136" y="110" width="48" height="86" rx="2" :fill="porte" stroke="#00000033" />
    <rect x="144" y="118" width="32" height="26" rx="2" fill="#ffffff55" />
    <circle cx="176" cy="158" r="2.5" fill="#f4f1e8" />
    <rect x="86" y="56" width="148" height="38" rx="5" fill="#ffffff" stroke="#00000022" />
    <image v-if="logo" :href="logo" x="92" y="61" width="28" height="28" preserveAspectRatio="xMidYMid meet" />
    <text
      :x="logo ? 126 : 160" :y="enseigne.lignes.length > 1 ? 72 : 80" :text-anchor="logo ? 'start' : 'middle'"
      :fill="texteEnseigne" :font-size="enseigne.taille" font-weight="700" font-family="inherit"
    >
      <tspan
        v-for="(ligne, i) in enseigne.lignes" :key="i" :x="logo ? 126 : 160" :dy="i ? enseigne.taille * 1.15 : 0"
      >{{ ligne }}</tspan>
    </text>
  </svg>
</template>

<style scoped>
.facade { display: block; width: 100%; height: auto; }
</style>
