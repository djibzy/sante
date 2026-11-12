<script setup lang="ts">
// Colonnes d'une seule série (chiffre d'affaires par jour ou par semaine) : barres de 24 px au
// plus, bout arrondi, grille discrète, valeur au survol et au clavier, chiffres en tableau.
const props = defineProps<{
  titre: string
  points: { debut: string, valeur: number, detail: string }[]
  pas: 'jour' | 'semaine'
}>()

const compact = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 })

/** Maximum arrondi (1, 2, 2,5 ou 5 × 10ⁿ) pour des graduations nettes. */
const maximum = computed(() => {
  const haut = Math.max(...props.points.map(p => p.valeur), 0)
  if (!haut) return 1
  const puissance = 10 ** Math.floor(Math.log10(haut))
  const pas = [1, 2, 2.5, 5, 10].find(m => m * puissance >= haut)!
  return pas * puissance
})
const graduations = computed(() => [0, 0.25, 0.5, 0.75, 1].map(f => f * maximum.value))
const etiquetteTous = computed(() => Math.max(1, Math.ceil(props.points.length / 6)))

function date(iso: string) {
  const jour = new Date(`${iso}T00:00:00Z`)
  return jour.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', timeZone: 'UTC' })
}
function libellePoint(iso: string) {
  return props.pas === 'semaine' ? `Semaine du ${date(iso)}` : date(iso)
}
</script>

<template>
  <figure class="graphique">
    <figcaption>{{ titre }}</figcaption>
    <div class="zone">
      <div class="axe" aria-hidden="true">
        <span v-for="g in [...graduations].reverse()" :key="g">{{ g ? compact.format(g) : '0' }}</span>
      </div>
      <div class="trace">
        <span v-for="g in graduations" :key="g" class="ligne" :style="{ bottom: `${(g / maximum) * 100}%` }" aria-hidden="true" />
        <div class="barres" :style="{ gap: points.length > 40 ? '1px' : '2px' }">
          <button
            v-for="(p, i) in points" :key="p.debut" type="button" class="colonne"
            :aria-label="`${libellePoint(p.debut)} : ${formaterFcfa(p.valeur)}, ${p.detail}`"
          >
            <span class="barre" :class="{ vide: !p.valeur }" :style="{ height: `${(p.valeur / maximum) * 100}%` }" />
            <span class="bulle" :class="{ gauche: i < points.length / 3, droite: i > (2 * points.length) / 3 }" role="tooltip">
              <strong>{{ formaterFcfa(p.valeur) }}</strong>
              <span>{{ libellePoint(p.debut) }} · {{ p.detail }}</span>
            </span>
            <span v-if="i % etiquetteTous === 0" class="date" aria-hidden="true">{{ date(p.debut) }}</span>
          </button>
        </div>
      </div>
    </div>
    <details class="chiffres">
      <summary>Voir les chiffres</summary>
      <table>
        <thead><tr><th scope="col">{{ pas === 'semaine' ? 'Semaine du' : 'Jour' }}</th><th scope="col">Montant</th><th scope="col">Détail</th></tr></thead>
        <tbody>
          <tr v-for="p in points" :key="p.debut"><td>{{ date(p.debut) }}</td><td>{{ formaterFcfa(p.valeur) }}</td><td>{{ p.detail }}</td></tr>
        </tbody>
      </table>
    </details>
  </figure>
</template>

<style scoped>
.graphique { margin: 0; display: grid; gap: 12px; }
figcaption { font-weight: 700; }
.zone { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px; height: 220px; padding-bottom: 22px; }
.axe { display: flex; flex-direction: column; justify-content: space-between; text-align: right; font-size: 0.75rem; color: var(--texte-doux); margin: -0.5em 0; }
.trace { position: relative; }
.ligne { position: absolute; left: 0; right: 0; height: 1px; background: var(--grille); }
.barres { position: absolute; inset: 0; display: flex; align-items: flex-end; }
.colonne {
  position: relative; flex: 1 1 0; min-width: 0; height: 100%; display: flex; align-items: flex-end;
  justify-content: center; padding: 0; border: 0; background: none; cursor: default;
}
.barre { width: 100%; max-width: 24px; border-radius: 4px 4px 0 0; background: var(--graphique); }
.barre.vide { height: 0 !important; }
.colonne:hover .barre, .colonne:focus-visible .barre { background: var(--graphique-survol); }
.colonne:focus-visible { outline: 2px solid var(--primaire); outline-offset: 2px; border-radius: 4px; }
.bulle {
  position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%); z-index: 2;
  display: none; gap: 2px; padding: 6px 10px; border-radius: 8px; background: var(--texte); color: #fff;
  font-size: 0.8rem; white-space: nowrap; pointer-events: none;
}
.bulle.gauche { left: 0; transform: none; }
.bulle.droite { left: auto; right: 0; transform: none; }
.bulle strong { font-size: 0.95rem; }
.colonne:hover .bulle, .colonne:focus-visible .bulle { display: grid; }
.date { position: absolute; top: 100%; margin-top: 4px; font-size: 0.72rem; color: var(--texte-doux); white-space: nowrap; }
.chiffres summary { cursor: pointer; color: var(--primaire); font-weight: 600; }
.chiffres table { margin-top: 8px; border-collapse: collapse; font-size: 0.9rem; }
.chiffres th, .chiffres td { padding: 4px 12px 4px 0; text-align: left; border-bottom: 1px solid var(--bordure); }
</style>
