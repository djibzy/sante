<script setup lang="ts">
import type { Metier, Rayon } from '~/types/catalogue'
import type { Exploration, Tuile } from '~/types/explorer'
import type { TenueProposee } from '~/types/tenues'

// Découverte visuelle : toutes les tenues en mur de couleurs, du blanc aux neutres. Les
// filtres sont dans l'adresse : une recherche se partage par WhatsApp.
useSeoMeta({
  title: 'Explorer par couleur',
  description: 'Toutes nos tenues médicales rangées par couleur : blouses, tuniques, pantalons, tenues de bloc, chaussures et accessoires.',
})
const route = useRoute()
const router = useRouter()
const adresse = useAdresseImage()
const texte = (valeur: unknown) => (typeof valeur === 'string' && valeur ? valeur : undefined)
// « proche » : couleur cherchée (rrggbb, sans #), venue d'une photo ou choisie à la main.
const hexa = (valeur: unknown) => (typeof valeur === 'string' && /^[0-9a-f]{6}$/i.test(valeur) ? valeur.toLowerCase() : undefined)
const filtres = computed(() => ({
  famille: texte(route.query.famille),
  metier: texte(route.query.metier),
  rayon: texte(route.query.rayon),
  genre: texte(route.query.genre),
  proche: hexa(route.query.proche),
}))
const requete = computed(() => ({ ...filtres.value, proche: filtres.value.proche ? `#${filtres.value.proche}` : undefined }))
const { data, status } = await useBoutiqueFetch<Exploration>('/api/v1/explorer', { query: requete })
const { data: idees } = await useBoutiqueFetch<TenueProposee[]>('/api/v1/tenues-proposees', {
  query: computed(() => ({ metier: filtres.value.metier })),
})
const montrerIdees = computed(() => !filtres.value.proche && !filtres.value.famille && !!idees.value?.length)
const { data: rayons } = await useBoutiqueFetch<Rayon[]>('/api/v1/rayons')
const { data: metiers } = await useBoutiqueFetch<Metier[]>('/api/v1/metiers')
const types = computed(() => (rayons.value ?? []).filter(r => r.univers === 'tenues'))
const metiersActifs = computed(() => (metiers.value ?? []).filter(m => m.nombre_produits))
const tuiles = computed(() => data.value?.tuiles ?? [])
const famille = computed(() => data.value?.familles.find(f => f.code === filtres.value.famille) ?? null)

function choisir(cle: 'famille' | 'metier' | 'rayon' | 'genre' | 'proche', valeur?: string) {
  const actuelle = filtres.value[cle]
  void router.replace({ query: { ...route.query, [cle]: valeur && valeur !== actuelle ? valeur : undefined } })
}
function valeurDe(evenement: Event) {
  return (evenement.target as HTMLSelectElement).value || undefined
}
const lien = (t: Tuile) => ({ path: `/produits/${t.produit_slug}`, query: { couleur: t.couleur } })
const actifs = computed(() => Object.values(filtres.value).some(Boolean))

// Recherche par la couleur d'une photo : calculée sur le téléphone, la photo n'est pas envoyée.
const apercu = ref<string | null>(null) // la photo, affichée en petit (adresse locale)
const couleursPhoto = ref<string[]>([])
const analyse = ref(false)
const erreurPhoto = ref('')
async function analyser(evenement: Event) {
  const champ = evenement.target as HTMLInputElement
  const fichier = champ.files?.[0]
  champ.value = '' // la même photo peut être reprise
  if (!fichier) return
  erreurPhoto.value = ''
  analyse.value = true
  try {
    couleursPhoto.value = await couleursDominantes(fichier)
    if (apercu.value) URL.revokeObjectURL(apercu.value)
    apercu.value = URL.createObjectURL(fichier)
    const premiere = couleursPhoto.value[0]
    if (premiere) await router.replace({ query: { ...route.query, proche: premiere.slice(1), famille: undefined } })
  } catch {
    erreurPhoto.value = 'Cette photo ne peut pas être lue. Essayez une photo JPEG ou PNG.'
  } finally {
    analyse.value = false
  }
}
function chercherCouleur(valeur: string) {
  void router.replace({ query: { ...route.query, proche: valeur.replace('#', ''), famille: undefined } })
}
function oublierCouleur() {
  if (apercu.value) URL.revokeObjectURL(apercu.value)
  apercu.value = null
  couleursPhoto.value = []
  choisir('proche')
}
onBeforeUnmount(() => { if (apercu.value) URL.revokeObjectURL(apercu.value) })
const proximite = (distance: number) => (distance < 6 ? 'Même couleur' : distance < 14 ? 'Très proche' : 'Proche')
</script>

<template>
  <section class="conteneur explorer">
    <header class="intro">
      <h1>Explorer par couleur</h1>
      <p>
        Toutes nos tenues, rangées par couleur. Choisissez une teinte, puis affinez par métier ou par type d'article.
        Ou <NuxtLink to="/composer">composez votre tenue</NuxtLink> sur le mannequin.
      </p>
    </header>

    <section v-if="montrerIdees" class="idees" aria-labelledby="titre-idees">
      <h2 id="titre-idees">Idées de tenues</h2>
      <div class="rangee-idees">
        <CarteTenue v-for="t in idees" :key="t.id" :tenue="t" />
      </div>
    </section>

    <div class="nuancier" role="group" aria-label="Familles de couleurs">
      <button type="button" class="nuance" :aria-pressed="!filtres.famille" @click="choisir('famille')">
        <span class="rond tout" aria-hidden="true" />
        <span class="nuance-nom">Toutes</span>
      </button>
      <button
        v-for="f in data?.familles ?? []" :key="f.code" type="button" class="nuance"
        :aria-pressed="filtres.famille === f.code" :disabled="!f.nombre && filtres.famille !== f.code"
        @click="choisir('famille', f.code)"
      >
        <span class="rond" :style="{ background: f.hex }" aria-hidden="true" />
        <span class="nuance-nom">{{ f.nom }}</span>
        <span class="nuance-nombre">{{ f.nombre }}<span class="visuellement-cache"> articles</span></span>
      </button>
    </div>

    <div class="par-couleur">
      <label class="bouton bouton-secondaire photo">
        <input type="file" accept="image/*" class="visuellement-cache" @change="analyser">
        <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" />
        </svg>
        {{ analyse ? 'Analyse de la photo…' : "Trouver la couleur d'une photo" }}
      </label>
      <label class="libre">
        ou choisir une couleur
        <input type="color" :value="`#${filtres.proche ?? '1f4fa8'}`" @change="chercherCouleur(($event.target as HTMLInputElement).value)">
      </label>
    </div>
    <p v-if="erreurPhoto" class="alerte alerte-erreur" role="alert">{{ erreurPhoto }}</p>
    <div v-if="filtres.proche" class="recherche-couleur carte">
      <img v-if="apercu" :src="apercu" alt="Votre photo" class="miniature">
      <div class="cherchee">
        <p>
          <span class="point grand" :style="{ background: `#${filtres.proche}` }" aria-hidden="true" />
          Tenues de couleur proche
        </p>
        <div v-if="couleursPhoto.length > 1" class="autres" role="group" aria-label="Couleurs de la photo">
          <span class="aide">Couleurs de la photo :</span>
          <button
            v-for="c in couleursPhoto" :key="c" type="button" class="echantillon" :style="{ background: c }"
            :aria-pressed="c === `#${filtres.proche}`" :aria-label="`Chercher la couleur ${c}`" @click="chercherCouleur(c)"
          />
        </div>
        <p v-if="apercu" class="aide">La photo reste sur votre téléphone : seule sa couleur sert à la recherche.</p>
      </div>
      <button type="button" class="bouton bouton-discret" @click="oublierCouleur">Effacer</button>
    </div>

    <div class="filtres">
      <label class="filtre">
        <span>Métier</span>
        <select :value="filtres.metier ?? ''" @change="choisir('metier', valeurDe($event))">
          <option value="">Tous les métiers</option>
          <option v-for="m in metiersActifs" :key="m.slug" :value="m.slug">{{ m.nom }}</option>
        </select>
      </label>
      <label class="filtre">
        <span>Type</span>
        <select :value="filtres.rayon ?? ''" @change="choisir('rayon', valeurDe($event))">
          <option value="">Tous les types</option>
          <option v-for="r in types" :key="r.slug" :value="r.slug">{{ r.nom }}</option>
        </select>
      </label>
      <div class="coupes" role="group" aria-label="Coupe">
        <button type="button" class="bouton bouton-secondaire" :aria-pressed="filtres.genre === 'femme'" @click="choisir('genre', 'femme')">Femme</button>
        <button type="button" class="bouton bouton-secondaire" :aria-pressed="filtres.genre === 'homme'" @click="choisir('genre', 'homme')">Homme</button>
      </div>
      <NuxtLink v-if="actifs" to="/explorer" class="effacer">Tout effacer</NuxtLink>
    </div>

    <p class="compte" role="status">
      <template v-if="status === 'pending'">Recherche…</template>
      <template v-else>
        {{ tuiles.length }} article{{ tuiles.length > 1 ? 's' : '' }}<template v-if="famille"> · {{ famille.nom.toLowerCase() }}</template>
      </template>
    </p>

    <ul v-if="tuiles.length" class="mur" :class="{ attente: status === 'pending' }">
      <li v-for="t in tuiles" :key="`${t.produit_slug}-${t.couleur}`">
        <NuxtLink :to="lien(t)" class="tuile" :style="{ '--teinte': t.hex }">
          <span class="visuel">
            <span v-if="t.distance !== null" class="proximite">{{ proximite(t.distance) }}</span>
            <img v-if="t.image" :src="adresse(t.image.url)" alt="" loading="lazy">
            <IllustrationArticle
              v-else-if="formeArticle(t.rayon_slug, t.produit_slug)"
              :forme="formeArticle(t.rayon_slug, t.produit_slug)!" :hex="t.hex" :couleur="t.couleur" fond
            />
            <ChartePictogramme v-else :type="t.rayon_slug" :taille="72" :teinte="t.hex" />
          </span>
          <span class="legende">
            <span class="nom">{{ t.nom }}</span>
            <span class="couleur"><span class="point" :style="{ background: t.hex }" aria-hidden="true" />{{ t.couleur }}</span>
            <span v-if="t.prix" class="prix">{{ formaterFcfa(t.prix) }}</span>
          </span>
        </NuxtLink>
      </li>
    </ul>
    <div v-else-if="status !== 'pending'" class="carte vide">
      <p v-if="filtres.proche">Aucune tenue d'une couleur proche. Essayez une autre couleur de la photo, ou une autre photo.</p>
      <p v-else>Aucune tenue dans cette couleur avec ces filtres.</p>
      <NuxtLink to="/explorer" class="bouton bouton-secondaire">Voir toutes les couleurs</NuxtLink>
    </div>
  </section>
</template>

<style scoped>
.explorer { padding-top: 20px; }
.intro h1 { margin: 0 0 4px; }
.intro p { margin: 0 0 16px; color: var(--texte-doux); max-width: 640px; }
/* position : les textes cachés (lecteurs d'écran) restent dans la zone qui défile. */
.nuancier { position: relative; display: flex; gap: 8px; overflow-x: auto; padding: 4px 2px 10px; margin: 0 -2px; scrollbar-width: thin; }
.nuance {
  flex: none; display: grid; justify-items: center; gap: 4px; min-width: 68px; padding: 8px 6px;
  border: 1.5px solid var(--bordure); border-radius: 14px; background: var(--surface); color: var(--texte);
  font: inherit; font-size: 0.8rem; cursor: pointer;
}
.nuance[aria-pressed='true'] { border-color: var(--primaire); background: var(--primaire-clair); }
.nuance:disabled { opacity: 0.4; cursor: default; }
.nuance:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.rond { width: 34px; height: 34px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.22); }
.rond.tout { background: conic-gradient(#e58fa5, #e07b1f, #2e8b6e, #1aa6a6, #1f4fa8, #6b2d5c, #e58fa5); }
.nuance-nom { font-weight: 650; line-height: 1.2; text-align: center; max-width: 92px; }
.nuance-nombre { color: var(--texte-doux); font-size: 0.75rem; }
.idees { margin: 4px 0 18px; }
.idees h2 { font-size: 1.15rem; margin: 0 0 10px; }
.rangee-idees { position: relative; display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
.par-couleur { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin: 4px 0 10px; }
.photo { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.photo:focus-within { outline: 3px solid var(--accent); outline-offset: 2px; }
.libre { display: inline-flex; align-items: center; gap: 8px; font-size: 0.92rem; color: var(--texte-doux); }
.libre input { width: 44px; height: 44px; padding: 2px; border: 1.5px solid var(--bordure); border-radius: 10px; background: var(--surface); cursor: pointer; }
.recherche-couleur { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 12px; margin-bottom: 12px; }
.recherche-couleur > .bouton { margin-left: auto; }
.miniature { width: 64px; height: 64px; object-fit: cover; border-radius: 10px; flex: none; }
.cherchee { flex: 1 1 210px; display: grid; gap: 4px; min-width: 0; }
.cherchee p { margin: 0; display: flex; align-items: center; gap: 8px; }
.cherchee p:first-child { font-weight: 650; }
.point.grand { width: 22px; height: 22px; }
.autres { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.echantillon { width: 28px; height: 28px; border-radius: 50%; border: 0; cursor: pointer; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.echantillon[aria-pressed='true'] { box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--primaire); }
.echantillon:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.proximite { position: absolute; top: 6px; left: 6px; padding: 2px 7px; border-radius: 999px; background: rgba(255, 255, 255, 0.92); color: var(--texte); font-size: 0.7rem; font-weight: 700; }
.filtres { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 10px 14px; margin: 8px 0 12px; }
.filtre { display: grid; gap: 4px; font-size: 0.85rem; font-weight: 650; }
.filtre select { min-height: 44px; padding: 0 0.6em; border: 1.5px solid var(--bordure); border-radius: 10px; background: var(--surface); font: inherit; font-weight: 400; }
.coupes { display: flex; gap: 6px; }
.coupes .bouton { min-height: 44px; }
.coupes .bouton[aria-pressed='true'] { background: var(--primaire); color: #fff; border-color: var(--primaire); }
.effacer { align-self: center; font-size: 0.92rem; }
.compte { margin: 0 0 10px; color: var(--texte-doux); font-size: 0.92rem; }
.mur {
  list-style: none; margin: 0; padding: 0; display: grid; gap: 10px;
  grid-template-columns: repeat(auto-fill, minmax(min(30%, 150px), 1fr)); transition: opacity 0.2s;
}
@media (min-width: 720px) { .mur { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; } }
.mur.attente { opacity: 0.55; }
.tuile { display: grid; gap: 6px; color: var(--texte); text-decoration: none; }
.visuel {
  position: relative; display: grid; place-items: center; aspect-ratio: 4 / 5; border-radius: 12px; overflow: hidden;
  background: var(--fond-doux); box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.06); transition: transform 0.15s, box-shadow 0.15s;
}
.visuel img { width: 100%; height: 100%; object-fit: cover; }
.tuile:hover .visuel, .tuile:focus-visible .visuel { transform: translateY(-2px); box-shadow: 0 0 0 2px var(--teinte), 0 6px 16px rgba(23, 21, 58, 0.12); }
.tuile:focus-visible { outline: none; }
.legende { display: grid; gap: 1px; font-size: 0.82rem; line-height: 1.3; }
.legende .nom { font-weight: 650; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.couleur { display: flex; align-items: center; gap: 5px; color: var(--texte-doux); }
.point { flex: none; width: 10px; height: 10px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.prix { font-weight: 750; }
.vide { padding: 24px; display: grid; justify-items: start; gap: 10px; }
</style>
