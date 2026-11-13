<script setup lang="ts">
import type { PageProduits, ProduitDetail } from '~/types/catalogue'

// Commande pour une équipe : le même article, une ligne par personne (nom brodé, taille,
// quantité). Une liste se colle depuis un tableur ou un message. Tout part au panier, d'où
// l'on commande ou demande un devis pour la structure.
useSeoMeta({ title: 'Commande pour une équipe', description: 'Une tenue brodée au nom de chaque membre de votre équipe : saisissez ou collez la liste des noms et des tailles.' })
const MAX_LIGNES = 50 // une commande ou un devis compte 50 lignes au plus

const route = useRoute()
const router = useRouter()
const slug = computed(() => (typeof route.query.produit === 'string' ? route.query.produit : ''))
const { data: produit, error } = await useBoutiqueFetch<ProduitDetail>(() => `/api/v1/produits/${slug.value || '_'}`)
const { data: brodables } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', { query: { univers: 'tenues', par_page: 60 } })
const choix = computed(() => (brodables.value?.elements ?? []).filter(p => p.personnalisable && p.vendable_en_ligne))

const demandee = typeof route.query.couleur === 'string' ? route.query.couleur : null
const couleur = ref<string | null>(null)
watch(produit, (p) => {
  couleur.value = p?.couleurs.find(c => c.nom === demandee)?.nom ?? p?.couleurs[0]?.nom ?? null
}, { immediate: true })
const teinte = computed(() => produit.value?.couleurs.find(c => c.nom === couleur.value)?.hex ?? null)
const forme = computed(() => (produit.value ? formeArticle(produit.value.rayon_slug, produit.value.slug) : null))

interface Personne { nom: string, taille: string, quantite: number }
const vide = (): Personne => ({ nom: '', taille: '', quantite: 1 })
const personnes = ref<Personne[]>([vide(), vide(), vide()])
const remplies = computed(() => personnes.value.filter(p => p.nom.trim() || p.taille))
const pieces = computed(() => remplies.value.reduce((n, p) => n + (Math.round(p.quantite) || 0), 0))
function prixPour(taille: string): number | null {
  const p = produit.value
  if (!p) return null
  const variante = p.variantes.find(v => (v.couleur ?? null) === (p.couleurs.length ? couleur.value : null) && (v.taille ?? null) === (taille || null))
  return variante?.prix ?? p.prix_public
}
const total = computed(() => remplies.value.reduce((t, p) => t + (prixPour(p.taille) ?? 0) * (Math.round(p.quantite) || 0), 0))
const tailleDisponible = (taille: string) => !!produit.value?.variantes.some(v => v.taille === taille && (!couleur.value || v.couleur === couleur.value))

// Liste collée : « Aminata Traoré, sage-femme ; M ; 2 » ou une colonne copiée d'un tableur.
// La taille et la quantité sont reconnues en fin de ligne ; le reste est le texte à broder.
const liste = ref('')
const importees = ref<number | null>(null)
function importer() {
  const tailles = new Map((produit.value?.tailles ?? []).map(t => [t.toLowerCase(), t]))
  const nouvelles: Personne[] = []
  for (const brute of liste.value.split(/\r?\n/)) {
    const morceaux = brute.split(/[\t;,]/).map(m => m.trim()).filter(Boolean)
    if (!morceaux.length) continue
    let quantite = 1
    let taille = ''
    if (morceaux.length > 1 && /^\d{1,3}$/.test(morceaux.at(-1)!)) quantite = Number(morceaux.pop())
    if (morceaux.length > 1 && tailles.has(morceaux.at(-1)!.toLowerCase())) taille = tailles.get(morceaux.pop()!.toLowerCase())!
    else if (morceaux.length > 1 && tailles.has(morceaux[0]!.toLowerCase())) taille = tailles.get(morceaux.shift()!.toLowerCase())!
    nouvelles.push({ nom: morceaux.join(', ').slice(0, 60), taille, quantite: Math.max(1, Math.min(500, quantite)) })
  }
  personnes.value = [...remplies.value, ...nouvelles].slice(0, MAX_LIGNES)
  importees.value = nouvelles.length
  liste.value = ''
}

const erreur = ref('')
const ajoute = ref(false)
const { ajouter } = usePanier()
function ajouterAuPanier() {
  erreur.value = ''
  ajoute.value = false
  const p = produit.value
  if (!p) return
  if (!remplies.value.length) {
    erreur.value = 'Ajoutez au moins une personne.'
    return
  }
  if (remplies.value.length > MAX_LIGNES) {
    erreur.value = `${MAX_LIGNES} personnes au plus par commande : pour plus, demandez-nous un devis.`
    return
  }
  const sansTaille = remplies.value.findIndex(r => p.tailles.length && !r.taille)
  if (sansTaille >= 0) {
    erreur.value = `Choisissez la taille de ${remplies.value[sansTaille]!.nom || `la ligne ${sansTaille + 1}`}.`
    return
  }
  for (const r of remplies.value) {
    const variante = p.variantes.find(v => (v.couleur ?? null) === (p.couleurs.length ? couleur.value : null) && (v.taille ?? null) === (r.taille || null))
    if (p.variantes.length && !variante) {
      erreur.value = `${p.nom} n'existe pas en ${r.taille} dans cette couleur.`
      return
    }
  }
  for (const r of remplies.value) {
    const variante = p.variantes.find(v => (v.couleur ?? null) === (p.couleurs.length ? couleur.value : null) && (v.taille ?? null) === (r.taille || null))
    ajouter({
      produit_id: p.id,
      variante_id: variante?.id ?? null,
      quantite: Math.max(1, Math.min(500, Math.round(r.quantite) || 1)),
      personnalisation: r.nom.trim() || null,
      slug: p.slug,
      nom: p.nom,
      variante: variante?.libelle ?? null,
      rayon_slug: p.rayon_slug,
      prix_indicatif: variante?.prix ?? p.prix_public,
    })
  }
  ajoute.value = true
}
function choisirProduit(nouveau: string) {
  void router.replace({ query: { produit: nouveau } })
}
</script>

<template>
  <section class="conteneur equipe">
    <h1>Commande pour une équipe</h1>
    <p class="intro">
      Le même article pour toute l'équipe, brodé au nom de chacun : saisissez ou collez la liste des
      noms et des tailles. Vous commandez ensuite, ou demandez un devis pour votre structure.
    </p>

    <div v-if="!produit || error" class="carte bloc">
      <h2>Quel article ?</h2>
      <div class="articles">
        <button v-for="p in choix" :key="p.slug" type="button" class="article" @click="choisirProduit(p.slug)">
          <span class="vignette">
            <IllustrationArticle
              v-if="formeArticle(p.rayon_slug, p.slug) && p.couleurs[0]?.hex"
              :forme="formeArticle(p.rayon_slug, p.slug)!" :hex="p.couleurs[0]!.hex!" :couleur="p.couleurs[0]!.nom" fond brode
            />
            <ChartePictogramme v-else :type="p.rayon_slug" :taille="64" />
          </span>
          <span class="nom">{{ p.nom }}</span>
          <span v-if="p.prix_public" class="aide">{{ formaterFcfa(p.prix_public) }}</span>
        </button>
      </div>
    </div>

    <div v-else class="colonnes">
      <div class="carte bloc article-choisi">
        <span class="vignette grande">
          <IllustrationArticle v-if="forme && teinte" :forme="forme" :hex="teinte" :couleur="couleur" fond brode :libelle="`${produit.nom}, ${couleur}`" />
          <ChartePictogramme v-else :type="produit.rayon_slug" :taille="96" :teinte="teinte" />
        </span>
        <div>
          <h2>{{ produit.nom }}</h2>
          <p class="aide">{{ produit.prix_public ? `${formaterFcfa(produit.prix_public)} la pièce` : '' }}</p>
          <div v-if="produit.couleurs.length > 1" class="couleurs" role="radiogroup" aria-label="Couleur pour toute l'équipe">
            <label v-for="c in produit.couleurs" :key="c.nom" class="couleur" :class="{ actif: couleur === c.nom }">
              <input v-model="couleur" type="radio" name="couleur" :value="c.nom" class="visuellement-cache">
              <span class="point" :style="{ background: c.hex ?? '#ccc' }" aria-hidden="true" />{{ c.nom }}
            </label>
          </div>
          <NuxtLink :to="{ path: '/commande-equipe' }" class="changer">Changer d'article</NuxtLink>
        </div>
      </div>

      <div class="carte bloc">
        <h2>L'équipe</h2>
        <div class="tableau" role="group" aria-label="Personnes de l'équipe">
          <div class="rangee entete" aria-hidden="true">
            <span>Texte à broder</span>
            <span>{{ produit.tailles.length ? 'Taille' : '' }}</span>
            <span>Qté</span>
            <span><span class="visuellement-cache">Retirer</span></span>
          </div>
          <div v-for="(p, i) in personnes" :key="i" class="rangee">
            <input v-model="p.nom" maxlength="60" :aria-label="`Texte à broder, ligne ${i + 1}`" :placeholder="i === 0 ? 'Aminata Traoré, sage-femme' : 'Nom et fonction à broder'">
            <select v-if="produit.tailles.length" v-model="p.taille" :aria-label="`Taille, ligne ${i + 1}`">
              <option value="">Taille</option>
              <option v-for="t in produit.tailles" :key="t" :value="t" :disabled="!tailleDisponible(t)">{{ t }}</option>
            </select>
            <span v-else />
            <label class="qte">
              <span aria-hidden="true">Qté</span>
              <input v-model.number="p.quantite" type="number" min="1" max="500" inputmode="numeric" :aria-label="`Quantité, ligne ${i + 1}`">
            </label>
            <button type="button" class="bouton bouton-discret retirer" :aria-label="`Retirer la ligne ${i + 1}`" @click="personnes.splice(i, 1)">×</button>
          </div>
        </div>
        <button type="button" class="bouton bouton-secondaire" :disabled="personnes.length >= MAX_LIGNES" @click="personnes.push(vide())">
          Ajouter une personne
        </button>

        <details class="coller">
          <summary>Coller une liste (tableur, message)</summary>
          <label for="liste" class="aide">Une personne par ligne : le texte à broder, puis la taille, puis la quantité si plus d'une.</label>
          <textarea id="liste" v-model="liste" rows="5" :placeholder="'Aminata Traoré, sage-femme ; M\nMoussa Diarra ; XL ; 2\nAwa Sidibé, infirmière ; S'" />
          <button type="button" class="bouton bouton-secondaire" :disabled="!liste.trim()" @click="importer">Importer la liste</button>
          <p v-if="importees !== null" class="aide" role="status">{{ importees }} personne{{ importees > 1 ? 's' : '' }} ajoutée{{ importees > 1 ? 's' : '' }}.</p>
        </details>
      </div>

      <div class="carte bloc resume">
        <p class="total">
          <span>{{ pieces }} pièce{{ pieces > 1 ? 's' : '' }}</span>
          <strong>{{ formaterFcfa(total) }}</strong>
        </p>
        <p v-if="produit.acompte_pourcent" class="aide">
          Articles brodés à la demande : un acompte de {{ produit.acompte_pourcent }} %, non remboursable, est demandé à la
          confirmation. Pour une structure, le prix professionnel s'applique sur devis.
        </p>
        <button type="button" class="bouton bouton-large" @click="ajouterAuPanier">Ajouter l'équipe au panier</button>
        <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
        <div v-if="ajoute" class="alerte alerte-succes" role="status">
          <p>{{ remplies.length }} ligne{{ remplies.length > 1 ? 's' : '' }} ajoutée{{ remplies.length > 1 ? 's' : '' }} au panier.</p>
          <div class="suite">
            <NuxtLink to="/panier" class="bouton bouton-secondaire">Voir le panier</NuxtLink>
            <NuxtLink to="/devis" class="bouton bouton-secondaire">Demander un devis</NuxtLink>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.equipe { padding-top: 20px; }
.intro { color: var(--texte-doux); max-width: 680px; margin: 0 0 16px; }
.colonnes { display: grid; gap: 14px; }
@media (min-width: 960px) { .colonnes { grid-template-columns: minmax(0, 1fr) 340px; } .colonnes > :nth-child(2) { grid-row: span 2; } }
.bloc { padding: 16px; display: grid; gap: 10px; align-content: start; }
.bloc h2 { margin: 0; font-size: 1.1rem; }
.bloc p { margin: 0; }
.articles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); }
.article {
  display: grid; gap: 4px; padding: 8px; border: 1.5px solid var(--bordure); border-radius: 12px; background: var(--surface);
  color: var(--texte); font: inherit; text-align: left; cursor: pointer;
}
.article:hover { border-color: var(--primaire); }
.article:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.article .nom { font-weight: 650; font-size: 0.9rem; }
.vignette { display: grid; place-items: center; aspect-ratio: 4 / 5; border-radius: 8px; overflow: hidden; background: var(--fond-doux); }
.article-choisi { grid-template-columns: 96px minmax(0, 1fr); align-items: start; }
.vignette.grande { width: 96px; }
.couleurs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.couleur {
  display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 0 12px; border: 1.5px solid var(--bordure);
  border-radius: 999px; cursor: pointer; font-size: 0.88rem; font-weight: 600;
}
.couleur.actif { border-color: var(--primaire); background: var(--primaire-clair); color: var(--primaire-fonce); }
.couleur:focus-within { outline: 3px solid var(--accent); outline-offset: 2px; }
.point { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.changer { display: inline-block; margin-top: 8px; font-size: 0.92rem; }
.tableau { display: grid; gap: 6px; }
.rangee { display: grid; grid-template-columns: minmax(0, 1fr) 84px 64px 36px; gap: 6px; align-items: center; }
.rangee.entete { font-size: 0.82rem; font-weight: 650; color: var(--texte-doux); }
.qte span { display: none; }
/* Téléphone : le nom sur toute la largeur, puis la taille et la quantité. */
@media (max-width: 560px) {
  .rangee { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 40px; padding-bottom: 8px; border-bottom: 1px solid var(--bordure); }
  .rangee > input:first-child { grid-column: 1 / -1; }
  .rangee.entete { display: none; }
  .qte { display: flex; align-items: center; gap: 6px; }
  .qte span { display: inline; font-size: 0.85rem; font-weight: 650; color: var(--texte-doux); }
}
.rangee input, .rangee select { min-height: 44px; width: 100%; min-width: 0; padding: 0 8px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; background: var(--surface); }
.retirer { min-height: 40px; padding: 0; font-size: 1.3rem; }
.coller summary { cursor: pointer; font-weight: 650; padding: 6px 0; }
.coller { display: grid; gap: 8px; }
.coller textarea { width: 100%; padding: 8px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; }
.coller .bouton { justify-self: start; }
@media (min-width: 960px) { .resume { position: sticky; top: 150px; } }
.total { display: flex; justify-content: space-between; align-items: baseline; font-size: 1.05rem; }
.total strong { font-size: 1.3rem; }
.suite { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
</style>
