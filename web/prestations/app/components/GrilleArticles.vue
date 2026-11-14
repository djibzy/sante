<script setup lang="ts">
import type { ArticleOffre } from '~/types/prestations'

// Une ligne par article, rangée par famille : quantités (comptage, volumes estimés) avec des
// boutons − et + faciles au pouce, ou prix en FCFA (tarifs d'un contrat ou d'un partenaire).
const props = withDefaults(defineProps<{
  articles: ArticleOffre[]
  mode?: 'quantite' | 'prix'
  identifiant: string // préfixe des id des champs, unique dans la page
  avecPrecision?: boolean // « autre » : une précision (nappes, tabliers…)
}>(), { mode: 'quantite', avecPrecision: true })
const valeurs = defineModel<Record<string, number | null>>({ required: true })
const precision = defineModel<string>('precision', { default: '' })

const familles = computed(() => {
  const groupes = new Map<string, { libelle: string; articles: ArticleOffre[] }>()
  for (const article of props.articles) {
    const groupe = groupes.get(article.famille) ?? { libelle: article.libelle_famille, articles: [] }
    groupe.articles.push(article)
    groupes.set(article.famille, groupe)
  }
  return [...groupes.values()]
})

function lire(code: string): number | null {
  const valeur = valeurs.value[code]
  return typeof valeur === 'number' && !Number.isNaN(valeur) ? valeur : null
}

function ecrire(code: string, brut: string | number | null) {
  const nombre = brut === '' || brut === null ? null : Math.max(0, Math.round(Number(brut)))
  valeurs.value = { ...valeurs.value, [code]: Number.isNaN(nombre) ? null : nombre }
}

function ajuster(code: string, pas: number) {
  ecrire(code, Math.max(0, (lire(code) ?? 0) + pas))
}
</script>

<template>
  <div class="grille-articles">
    <fieldset v-for="famille in familles" :key="famille.libelle" class="famille">
      <legend>{{ famille.libelle }}</legend>
      <div v-for="article in famille.articles" :key="article.code" class="ligne">
        <label :for="`${identifiant}-${article.code}`">
          {{ article.libelle }}
          <small v-if="article.note" class="aide">{{ article.note }}</small>
        </label>
        <div v-if="mode === 'quantite'" class="compteur">
          <button type="button" class="pas" :aria-label="`${article.libelle} : une pièce de moins`" @click="ajuster(article.code, -1)">−</button>
          <input
            :id="`${identifiant}-${article.code}`" type="number" inputmode="numeric" min="0" max="10000" step="1"
            :value="lire(article.code) ?? ''" placeholder="0" @input="ecrire(article.code, ($event.target as HTMLInputElement).value)"
          >
          <button type="button" class="pas" :aria-label="`${article.libelle} : une pièce de plus`" @click="ajuster(article.code, 1)">+</button>
        </div>
        <div v-else class="prix">
          <input
            :id="`${identifiant}-${article.code}`" type="number" inputmode="numeric" min="0" step="25"
            :value="lire(article.code) ?? ''" placeholder="—" @input="ecrire(article.code, ($event.target as HTMLInputElement).value)"
          >
          <span aria-hidden="true">FCFA</span>
        </div>
        <div v-if="article.code === 'autre' && avecPrecision && (lire('autre') ?? 0) > 0" class="precision champ">
          <label :for="`${identifiant}-precision`">Quelle pièce ?</label>
          <input :id="`${identifiant}-precision`" v-model="precision" maxlength="80" placeholder="Nappes, tabliers…" required>
        </div>
      </div>
    </fieldset>
  </div>
</template>

<style scoped>
.grille-articles { display: grid; gap: 12px; max-width: 620px; }
.famille { border: 1px solid var(--bordure); border-radius: 12px; padding: 8px 12px 4px; margin: 0; min-width: 0; }
.famille legend { font-weight: 750; padding: 0 6px; }
.ligne { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; align-items: center; padding: 6px 0; border-top: 1px solid var(--fond-doux); }
.ligne:first-of-type { border-top: 0; }
.ligne label { font-weight: 600; }
.ligne small { display: block; font-weight: 400; }
.compteur, .prix { display: flex; align-items: center; gap: 4px; }
.compteur input { width: 4.2em; text-align: center; }
.prix input { width: 6.5em; text-align: right; }
.compteur input, .prix input { min-height: 44px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; padding: 0 0.4em; background: var(--surface); color: inherit; }
.pas { width: 44px; height: 44px; border-radius: 10px; border: 1.5px solid var(--bordure); background: var(--fond-doux); font: inherit; font-size: 1.3rem; font-weight: 700; cursor: pointer; color: var(--texte); }
.pas:hover { background: var(--primaire-clair); }
.precision { grid-column: 1 / -1; margin: 4px 0 6px; }
</style>
