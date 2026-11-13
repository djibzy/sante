<script setup lang="ts">
import type { Couleur, PageProduits, ProduitDetail, ProduitResume } from '~/types/catalogue'
import type { TenueGestion, TenueProposee } from '~/types/tenues'
import type { PieceHabillee } from '~/utils/formes'

// Cabine d'essayage : chaque pièce et sa couleur habillent le mannequin, puis toute la tenue
// part au panier. La tenue est dans l'adresse : elle se partage par WhatsApp.
useSeoMeta({
  title: 'Composer ma tenue',
  description: 'Essayez les couleurs : tunique, pantalon, blouse, chaussures et calot sur un mannequin, puis ajoutez toute la tenue au panier.',
})

type Cle = 'haut' | 'bas' | 'dessus' | 'chaussures' | 'calot'
interface Rubrique { cle: Cle, titre: string, formes: string[], facultatif: boolean }
const RUBRIQUES: Rubrique[] = [
  { cle: 'haut', titre: 'Haut', formes: ['tunique', 'polo', 'tshirt'], facultatif: true },
  { cle: 'bas', titre: 'Pantalon', formes: ['pantalon', 'pantalon-cargo'], facultatif: true },
  { cle: 'dessus', titre: 'Blouse ou gilet par-dessus', formes: ['blouse', 'gilet'], facultatif: true },
  { cle: 'chaussures', titre: 'Chaussures', formes: ['basket', 'sabot'], facultatif: true },
  { cle: 'calot', titre: 'Calot', formes: ['calot'], facultatif: true },
]
const BLANC = '#f1f0f6' // article sans couleur indiquée

const route = useRoute()
const router = useRouter()
const { appeler } = useApiBoutique()
const { ajouter } = usePanier()
// Toutes les tenues tiennent dans une page (une soixantaine d'articles au plus pour l'instant).
const { data: page } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', { query: { univers: 'tenues', par_page: 60 } })
const produits = computed(() => (page.value?.elements ?? []).filter(p => p.vendable_en_ligne))
const { data: idees } = await useBoutiqueFetch<TenueProposee[]>('/api/v1/tenues-proposees')
function partirDe(idee: TenueProposee) {
  ajoute.value = false
  for (const cle of Object.keys(tailles) as Cle[]) tailles[cle] = ''
  void router.replace({ query: habiller(idee.pieces).requete })
}
const forme = (p: ProduitResume) => formeArticle(p.rayon_slug, p.slug)
const articles = (r: Rubrique) => produits.value.filter(p => r.formes.includes(forme(p) ?? ''))

// Sans rien dans l'adresse : une tunique et un pantalon blanc pour commencer.
const texte = (v: unknown) => (typeof v === 'string' && v ? v : null)
const vierge = computed(() => !('vide' in route.query) && !RUBRIQUES.some(r => r.cle in route.query))
const uni = (p: ProduitResume) => !p.couleurs[0]?.nom.toLowerCase().startsWith('wax')
function selection(r: Rubrique): { produit: ProduitResume, couleur: Couleur | null } | null {
  const defaut = vierge.value && (r.cle === 'haut' || r.cle === 'bas') ? articles(r).find(uni) ?? articles(r)[0] : undefined
  const produit = articles(r).find(p => p.slug === texte(route.query[r.cle])) ?? defaut
  if (!produit) return null
  const demandee = texte(route.query[`${r.cle}_couleur`]) ?? (vierge.value && r.cle === 'bas' ? 'Blanc' : null)
  const couleur = produit.couleurs.find(c => c.nom === demandee && c.hex) ?? produit.couleurs.find(c => c.hex) ?? null
  return { produit, couleur }
}
const choisis = computed(() => Object.fromEntries(RUBRIQUES.map(r => [r.cle, selection(r)])) as Record<Cle, ReturnType<typeof selection>>)

function requeteActuelle(): Record<string, string> {
  const requete: Record<string, string> = {}
  for (const r of RUBRIQUES) {
    const choisi = choisis.value[r.cle]
    if (!choisi) continue
    requete[r.cle] = choisi.produit.slug
    if (choisi.couleur) requete[`${r.cle}_couleur`] = choisi.couleur.nom
  }
  return requete
}
function mettreAJour(changements: Record<string, string | undefined>) {
  ajoute.value = false
  const requete: Record<string, string | undefined> = { ...requeteActuelle(), ...changements }
  if (!Object.values(requete).some(Boolean)) requete.vide = '1' // tout retiré : rester sans défaut
  else delete requete.vide
  void router.replace({ query: requete })
}
function choisirProduit(cle: Cle, slug?: string) {
  tailles[cle] = ''
  mettreAJour({ [cle]: slug, [`${cle}_couleur`]: undefined })
}

// Le mannequin, la description pour les lecteurs d'écran, le total.
function piece(cle: Cle): PieceHabillee | null {
  const choisi = choisis.value[cle]
  const f = choisi ? forme(choisi.produit) : null
  if (!choisi || !f) return null
  return { forme: f, hex: choisi.couleur?.hex ?? BLANC, couleur: choisi.couleur?.nom ?? null, brode: choisi.produit.personnalisable }
}
const habits = computed(() => Object.fromEntries(RUBRIQUES.map(r => [r.cle, piece(r.cle)])))
const resume = computed(() => RUBRIQUES.map(r => choisis.value[r.cle])
  .filter((c): c is NonNullable<typeof c> => !!c)
  .map(c => (c.couleur ? `${c.produit.nom} (${c.couleur.nom})` : c.produit.nom)))
const description = computed(() => (resume.value.length ? `Mannequin vêtu de : ${resume.value.join(', ')}` : 'Mannequin sans vêtement choisi'))
const total = computed(() => RUBRIQUES.reduce((somme, r) => somme + (choisis.value[r.cle]?.produit.prix_public ?? 0), 0))

// Couleurs assorties au haut choisi : ton sur ton, ou neutres (blanc, gris, bleu marine).
function accord(cle: Cle, hex: string | null): string | null {
  const repere = choisis.value.haut?.couleur?.hex
  if (cle === 'haut' || !hex || !repere) return null
  if (ecart(hex, repere) < 10) return 'ton sur ton'
  return estNeutre(hex) ? 'neutre' : null
}
const vignette = (r: Rubrique, p: ProduitResume) => {
  const choisi = choisis.value[r.cle]
  if (choisi?.produit.slug === p.slug && choisi.couleur) return choisi.couleur
  return p.couleurs.find(c => c.hex) ?? null
}

const tailles = reactive<Record<Cle, string>>({ haut: '', bas: '', dessus: '', chaussures: '', calot: '' })
const broderie = ref('')
const brodable = computed(() => RUBRIQUES.some(r => choisis.value[r.cle]?.produit.personnalisable))
const envoi = ref(false)
const erreur = ref('')
const ajoute = ref(false)

async function ajouterTenue() {
  erreur.value = ''
  const pieces = RUBRIQUES.flatMap(r => (choisis.value[r.cle] ? [{ r, choisi: choisis.value[r.cle]! }] : []))
  if (!pieces.length) {
    erreur.value = 'Choisissez au moins une pièce.'
    return
  }
  const sansTaille = pieces.find(({ r, choisi }) => choisi.produit.tailles.length && !tailles[r.cle])
  if (sansTaille) {
    erreur.value = `Choisissez la taille : ${sansTaille.r.titre.toLowerCase()}.`
    return
  }
  envoi.value = true
  try {
    const fiches = await Promise.all(pieces.map(({ choisi }) => appeler<ProduitDetail>(`/api/v1/produits/${choisi.produit.slug}`)))
    const lignes = pieces.map(({ r, choisi }, i) => {
      const fiche = fiches[i]!
      const variante = fiche.variantes.find(v =>
        (v.couleur ?? null) === (fiche.couleurs.length ? choisi.couleur?.nom ?? null : null)
        && (v.taille ?? null) === (fiche.tailles.length ? tailles[r.cle] : null))
      if (fiche.variantes.length && !variante) {
        throw new Error(`${fiche.nom} n'existe pas en ${tailles[r.cle]} dans cette couleur.`)
      }
      return {
        produit_id: fiche.id,
        variante_id: variante?.id ?? null,
        quantite: 1,
        personnalisation: fiche.personnalisable ? broderie.value.trim() || null : null,
        slug: fiche.slug,
        nom: fiche.nom,
        variante: variante?.libelle ?? null,
        rayon_slug: fiche.rayon_slug,
        prix_indicatif: variante?.prix ?? fiche.prix_public,
      }
    })
    lignes.forEach(ajouter)
    ajoute.value = true
  } catch (e) {
    erreur.value = e instanceof Error && !('status' in e) ? e.message : messageErreur(e)
  } finally {
    envoi.value = false
  }
}

// L'équipe enregistre la tenue composée comme idée proposée aux clients.
const { autorise: equipe } = useEquipe()
const proposition = reactive({ nom: '', description: '', metier: '' })
const proposee = ref<TenueGestion | null>(null)
const { data: metiers } = await useBoutiqueFetch<{ slug: string, nom: string }[]>('/api/v1/metiers')
async function proposer() {
  erreur.value = ''
  proposee.value = null
  try {
    proposee.value = await appeler<TenueGestion>('/api/v1/admin/tenues-proposees', {
      method: 'POST',
      body: {
        nom: proposition.nom,
        description: proposition.description,
        metier: proposition.metier || null,
        pieces: RUBRIQUES.flatMap(r => {
          const choisi = choisis.value[r.cle]
          return choisi ? [{ piece: r.cle, produit_id: choisi.produit.id, couleur: choisi.couleur?.nom ?? null }] : []
        }),
      },
    })
    proposition.nom = ''
    proposition.description = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

const partage = computed(() => {
  if (!import.meta.client || !resume.value.length) return ''
  const adresse = new URL('/composer', window.location.origin)
  for (const [cle, valeur] of Object.entries(requeteActuelle())) adresse.searchParams.set(cle, valeur)
  return `https://wa.me/?text=${encodeURIComponent(`Ma tenue Bibou : ${resume.value.join(', ')}. ${adresse.href}`)}`
})
</script>

<template>
  <section class="conteneur composer">
    <header class="intro">
      <h1>Composer ma tenue</h1>
      <p>Choisissez chaque pièce et sa couleur : le mannequin s'habille au fur et à mesure. Puis ajoutez toute la tenue au panier.</p>
    </header>

    <div v-if="idees?.length" class="idees" role="group" aria-label="Idées de tenues">
      <span class="etiquette">Partir d'une idée :</span>
      <button v-for="i in idees" :key="i.id" type="button" class="idee" @click="partirDe(i)">
        <span class="points" aria-hidden="true">
          <span v-for="p in i.pieces" :key="p.piece" class="point" :style="{ background: p.hex ?? BLANC }" />
        </span>
        {{ i.nom }}
      </button>
    </div>

    <div class="colonnes">
      <div class="apercu carte">
        <Mannequin v-bind="habits" :libelle="description" />
        <p class="total">
          <span>{{ resume.length }} pièce{{ resume.length > 1 ? 's' : '' }}</span>
          <strong>{{ formaterFcfa(total) }}</strong>
        </p>
      </div>

      <div class="rubriques">
        <fieldset v-for="r in RUBRIQUES" :key="r.cle" class="rubrique carte">
          <legend>{{ r.titre }}</legend>
          <div class="articles">
            <label class="article" :class="{ actif: !choisis[r.cle] }">
              <input type="radio" :name="r.cle" :checked="!choisis[r.cle]" class="visuellement-cache" @change="choisirProduit(r.cle)">
              <span class="vignette aucun" aria-hidden="true">—</span>
              <span class="nom">Sans</span>
            </label>
            <label
              v-for="p in articles(r)" :key="p.slug" class="article"
              :class="{ actif: choisis[r.cle]?.produit.slug === p.slug }"
            >
              <input
                type="radio" :name="r.cle" :value="p.slug" :checked="choisis[r.cle]?.produit.slug === p.slug"
                class="visuellement-cache" @change="choisirProduit(r.cle, p.slug)"
              >
              <span class="vignette">
                <IllustrationArticle :forme="forme(p)!" :hex="vignette(r, p)?.hex ?? BLANC" :couleur="vignette(r, p)?.nom" fond />
              </span>
              <span class="nom">{{ p.nom }}</span>
              <span class="prix">{{ p.prix_public ? formaterFcfa(p.prix_public) : '' }}</span>
            </label>
          </div>

          <template v-if="choisis[r.cle]">
            <div v-if="choisis[r.cle]!.produit.couleurs.length > 1" class="couleurs" role="radiogroup" :aria-label="`Couleur : ${r.titre}`">
              <label
                v-for="c in choisis[r.cle]!.produit.couleurs.filter(c => c.hex)" :key="c.nom" class="couleur"
                :class="{ actif: choisis[r.cle]!.couleur?.nom === c.nom }"
              >
                <input
                  type="radio" :name="`${r.cle}-couleur`" :checked="choisis[r.cle]!.couleur?.nom === c.nom" class="visuellement-cache"
                  @change="mettreAJour({ [`${r.cle}_couleur`]: c.nom })"
                >
                <span class="point" :style="{ background: c.hex! }" aria-hidden="true" />
                {{ c.nom }}
                <small v-if="accord(r.cle, c.hex)" class="accord">{{ accord(r.cle, c.hex) }}</small>
              </label>
            </div>
            <p v-else-if="choisis[r.cle]!.couleur" class="aide">Couleur : {{ choisis[r.cle]!.couleur!.nom }}</p>
            <div v-if="choisis[r.cle]!.produit.tailles.length" class="tailles" role="radiogroup" :aria-label="`${r.cle === 'chaussures' ? 'Pointure' : 'Taille'} : ${r.titre}`">
              <span class="etiquette">{{ r.cle === 'chaussures' ? 'Pointure' : 'Taille' }}</span>
              <label v-for="t in choisis[r.cle]!.produit.tailles" :key="t" class="taille" :class="{ actif: tailles[r.cle] === t }">
                <input v-model="tailles[r.cle]" type="radio" :name="`${r.cle}-taille`" :value="t" class="visuellement-cache">
                {{ t }}
              </label>
            </div>
          </template>
        </fieldset>

        <div v-if="brodable" class="champ broderie carte">
          <label for="broderie">Texte à broder (facultatif)</label>
          <input id="broderie" v-model="broderie" maxlength="60" placeholder="Aminata Traoré, sage-femme">
          <span class="aide">Brodé sur les pièces qui s'y prêtent. Un article brodé est fait pour vous : un acompte est demandé à la confirmation.</span>
        </div>

        <div class="fin carte">
          <p class="total-fin">Total de la tenue : <strong>{{ formaterFcfa(total) }}</strong></p>
          <button type="button" class="bouton bouton-large" :disabled="envoi" @click="ajouterTenue">
            {{ envoi ? 'Ajout…' : 'Ajouter la tenue au panier' }}
          </button>
          <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
          <p v-if="ajoute" class="alerte alerte-succes" role="status">
            Tenue ajoutée au panier. <NuxtLink to="/panier">Voir le panier</NuxtLink>
          </p>
          <a v-if="partage" :href="partage" target="_blank" rel="noopener" class="bouton bouton-secondaire bouton-large">Envoyer ma tenue sur WhatsApp</a>
        </div>

        <form v-if="equipe && resume.length >= 2" class="proposer carte" @submit.prevent="proposer">
          <h2>Proposer cette tenue aux clients</h2>
          <p class="aide">Réservé à l'équipe : la tenue apparaît dans « Idées de tenues » (page Explorer et composeur).</p>
          <div class="champ">
            <label for="nom-tenue">Nom</label>
            <input id="nom-tenue" v-model="proposition.nom" required minlength="3" maxlength="80" placeholder="La tenue du bloc">
          </div>
          <div class="champ">
            <label for="description-tenue">Description (facultatif)</label>
            <input id="description-tenue" v-model="proposition.description" maxlength="300">
          </div>
          <div class="champ">
            <label for="metier-tenue">Métier</label>
            <select id="metier-tenue" v-model="proposition.metier">
              <option value="">Tous les métiers</option>
              <option v-for="m in metiers ?? []" :key="m.slug" :value="m.slug">{{ m.nom }}</option>
            </select>
          </div>
          <button type="submit" class="bouton bouton-secondaire">Enregistrer l'idée de tenue</button>
          <p v-if="proposee" class="alerte alerte-succes" role="status">
            « {{ proposee.nom }} » est proposée aux clients. <NuxtLink to="/gestion/tenues">Voir les tenues proposées</NuxtLink>
          </p>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.composer { padding-top: 20px; }
.intro h1 { margin: 0 0 4px; }
.intro p { margin: 0 0 16px; color: var(--texte-doux); max-width: 640px; }
.colonnes { display: grid; gap: 16px; }
.apercu {
  position: sticky; top: 72px; z-index: 5; display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 8px;
  height: 230px; padding: 10px 14px; background: linear-gradient(var(--fond-doux), var(--surface));
}
.apercu .mannequin { height: 210px; }
.total { margin: 0; display: grid; justify-items: end; gap: 2px; font-size: 0.9rem; color: var(--texte-doux); }
.total strong { font-size: 1.2rem; color: var(--texte); }
@media (min-width: 900px) {
  .colonnes { grid-template-columns: 360px minmax(0, 1fr); align-items: start; }
  .apercu { top: 150px; height: auto; grid-template-columns: 1fr; padding: 20px; }
  .apercu .mannequin { height: 520px; }
  .total { justify-items: center; }
}
.rubriques { display: grid; gap: 12px; min-width: 0; }
.rubrique { margin: 0; padding: 14px; border: 1px solid var(--bordure); display: grid; gap: 10px; min-width: 0; }
.rubrique legend { float: left; width: 100%; padding: 0; font-weight: 750; font-size: 1.05rem; }
.articles { position: relative; display: flex; gap: 8px; overflow-x: auto; padding: 2px 2px 6px; scrollbar-width: thin; }
.article {
  flex: none; width: 104px; display: grid; gap: 3px; padding: 6px; border: 1.5px solid var(--bordure); border-radius: 12px;
  background: var(--surface); cursor: pointer; font-size: 0.8rem; line-height: 1.25; align-content: start;
}
.article.actif { border-color: var(--primaire); box-shadow: 0 0 0 1px var(--primaire); }
.article:focus-within { outline: 3px solid var(--accent); outline-offset: 2px; }
.vignette { display: grid; place-items: center; aspect-ratio: 4 / 5; border-radius: 8px; overflow: hidden; background: var(--fond-doux); }
.vignette.aucun { color: var(--texte-doux); font-size: 1.4rem; }
.article .nom { font-weight: 650; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.article .prix { color: var(--texte-doux); }
.couleurs, .tailles { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.couleur, .taille {
  display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 0 12px; border: 1.5px solid var(--bordure);
  border-radius: 999px; background: var(--surface); cursor: pointer; font-size: 0.88rem; font-weight: 600;
}
.couleur.actif, .taille.actif { border-color: var(--primaire); background: var(--primaire-clair); color: var(--primaire-fonce); }
.couleur:focus-within, .taille:focus-within { outline: 3px solid var(--accent); outline-offset: 2px; }
.point { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.accord { color: var(--succes); font-weight: 700; font-size: 0.75rem; }
.etiquette { font-size: 0.85rem; font-weight: 650; margin-right: 4px; }
.taille { min-width: 46px; justify-content: center; }
.broderie { padding: 14px; margin: 0; }
.idees { position: relative; display: flex; gap: 8px; align-items: center; overflow-x: auto; padding: 2px 2px 10px; margin-bottom: 4px; scrollbar-width: thin; }
.idees .etiquette { flex: none; }
.idee {
  flex: none; display: inline-flex; align-items: center; gap: 8px; min-height: 40px; padding: 0 12px; border: 1.5px solid var(--bordure);
  border-radius: 999px; background: var(--surface); color: var(--texte); font: inherit; font-size: 0.88rem; font-weight: 600; cursor: pointer;
}
.idee:hover { border-color: var(--primaire); }
.idee:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.points { display: inline-flex; gap: 3px; }
.idee .point { width: 12px; height: 12px; }
.proposer { padding: 14px; display: grid; gap: 4px; }
.proposer h2 { margin: 0; font-size: 1.05rem; }
.proposer .bouton { justify-self: start; }
.fin { padding: 14px; display: grid; gap: 10px; }
.fin p { margin: 0; }
.total-fin { font-size: 1.05rem; }
</style>
