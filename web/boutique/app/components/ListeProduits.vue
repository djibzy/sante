<script setup lang="ts">
import type { PageProduits } from '~/types/catalogue'

// Liste filtrable : le cadre (rayon, métier, nouveautés…) vient de la page, les filtres choisis
// par le visiteur vivent dans l'adresse, pour pouvoir partager une sélection.
const props = defineProps<{ cadre: Record<string, string | boolean> }>()
const route = useRoute()
const router = useRouter()
const FILTRES = ['metier', 'genre', 'couleur', 'taille', 'collection'] as const
const TRIS: Record<string, string> = {
  pertinence: 'Pertinence', nouveautes: 'Nouveautés', prix_croissant: 'Prix croissant', prix_decroissant: 'Prix décroissant',
}
const choisis = computed(() => Object.fromEntries(
  FILTRES.filter(f => typeof route.query[f] === 'string' && !(f in props.cadre)).map(f => [f, String(route.query[f])]),
))
const tri = computed(() => (typeof route.query.tri === 'string' && route.query.tri in TRIS ? route.query.tri : 'pertinence'))
const page = computed(() => Number(route.query.page) || 1)
const { data, status } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', {
  query: computed(() => ({ ...props.cadre, ...choisis.value, tri: tri.value, page: page.value, par_page: 24 })),
})
const filtresOuverts = ref(false)

function choisir(filtre: string, valeur: string | null) {
  const query = { ...route.query, page: undefined, [filtre]: valeur && route.query[filtre] !== valeur ? valeur : undefined }
  void router.replace({ query })
}
function trier(valeur: string) {
  void router.replace({ query: { ...route.query, tri: valeur === 'pertinence' ? undefined : valeur, page: undefined } })
}
function effacer() {
  void router.replace({ query: { q: route.query.q } })
}
const groupes = computed(() => {
  const f = data.value?.facettes
  if (!f) return []
  return [
    { cle: 'metier', titre: 'Métier', valeurs: f.metiers },
    { cle: 'genre', titre: 'Pour', valeurs: f.genres },
    { cle: 'couleur', titre: 'Couleur', valeurs: f.couleurs },
    { cle: 'taille', titre: 'Taille', valeurs: f.tailles },
    { cle: 'collection', titre: 'Collection', valeurs: f.collections },
  ].filter(g => !(g.cle in props.cadre) && g.valeurs.length > 1)
})
const nombreChoisis = computed(() => Object.keys(choisis.value).length)
</script>

<template>
  <div class="liste">
    <div class="barre-outils">
      <button type="button" class="bouton bouton-secondaire ouvrir-filtres" :aria-expanded="filtresOuverts" @click="filtresOuverts = !filtresOuverts">
        Filtres<span v-if="nombreChoisis"> ({{ nombreChoisis }})</span>
      </button>
      <span class="aide" aria-live="polite">{{ data?.total ?? 0 }} article{{ (data?.total ?? 0) > 1 ? 's' : '' }}</span>
      <label class="tri">
        <span class="visuellement-cache">Trier par</span>
        <select :value="tri" @change="trier(($event.target as HTMLSelectElement).value)">
          <option v-for="(libelle, cle) in TRIS" :key="cle" :value="cle">{{ libelle }}</option>
        </select>
      </label>
    </div>

    <div class="colonnes">
      <aside class="filtres" :class="{ ouverts: filtresOuverts }" aria-label="Filtres">
        <fieldset v-for="g in groupes" :key="g.cle" class="groupe">
          <legend>{{ g.titre }}</legend>
          <div :class="g.cle === 'couleur' ? 'valeurs couleurs' : g.cle === 'taille' ? 'valeurs tailles' : 'valeurs'">
            <button
              v-for="v in g.valeurs" :key="v.valeur" type="button" class="valeur"
              :class="{ actif: choisis[g.cle] === v.valeur }" :aria-pressed="choisis[g.cle] === v.valeur"
              @click="choisir(g.cle, v.valeur)"
            >
              <span v-if="g.cle === 'couleur'" class="teinte" :style="{ background: v.hex ?? '#ccc' }" />
              <span>{{ v.libelle }}</span>
              <small v-if="g.cle !== 'taille'">{{ v.nombre }}</small>
            </button>
          </div>
        </fieldset>
        <button v-if="nombreChoisis" type="button" class="bouton bouton-discret" @click="effacer">Effacer les filtres</button>
      </aside>

      <div class="resultats" :class="{ attente: status === 'pending' }">
        <GrilleProduits :produits="data?.elements ?? []" />
        <NavigationPages v-if="data" :page="data.page" :total="data.total" :par-page="data.par_page" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.barre-outils { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.barre-outils .aide { flex: 1; }
.tri select { min-height: 42px; padding: 0 10px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; background: var(--surface); }
.colonnes { display: grid; gap: 24px; }
@media (min-width: 960px) {
  .colonnes { grid-template-columns: 230px minmax(0, 1fr); align-items: start; }
  .ouvrir-filtres { display: none; }
}
.filtres { display: none; gap: 18px; }
.filtres.ouverts { display: grid; }
@media (min-width: 960px) { .filtres { display: grid; position: sticky; top: 130px; } }
.groupe { border: 0; padding: 0; margin: 0; }
.groupe legend { font-weight: 750; margin-bottom: 8px; }
.valeurs { display: grid; gap: 4px; }
.valeurs.tailles { display: flex; flex-wrap: wrap; gap: 6px; }
.valeur {
  display: flex; align-items: center; gap: 8px; width: 100%; padding: 6px 8px; border: 0; border-radius: 8px;
  background: transparent; font: inherit; color: inherit; text-align: left; cursor: pointer;
}
.valeur small { margin-left: auto; color: var(--texte-doux); }
.valeur:hover { background: var(--fond-doux); }
.valeur.actif { background: var(--primaire-clair); color: var(--primaire-fonce); font-weight: 700; }
.tailles .valeur { width: auto; min-width: 44px; justify-content: center; border: 1.5px solid var(--bordure); }
.tailles .valeur.actif { border-color: var(--primaire); }
.teinte { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); flex-shrink: 0; }
.resultats { transition: opacity 0.2s; }
.resultats.attente { opacity: 0.6; }
</style>
