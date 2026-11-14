<script setup lang="ts">
import type { PageProduits, ProduitResume } from '~/types/catalogue'
import type { PieceHabillee } from '~/utils/formes'

// « Votre structure à vos couleurs » : du logo à la peinture des murs et aux tenues de
// l'équipe. Le logo est lu dans le navigateur et ne quitte pas le téléphone ; la palette se
// partage par un lien (sans le logo) et le projet part par WhatsApp vers l'équipe.
useSeoMeta({
  title: 'Votre structure à vos couleurs',
  description: "Déposez le logo de votre centre de santé, clinique ou pharmacie : votre palette, la peinture RAL la plus proche pour vos murs, et votre équipe habillée à vos couleurs, logo brodé.",
})

const route = useRoute()
const config = useRuntimeConfig()
const { data: page } = await useBoutiqueFetch<PageProduits>('/api/v1/produits', { query: { univers: 'tenues', par_page: 60 } })

const MAX_COULEURS = 4
const ROLES = ['Couleur principale', 'Deuxième couleur', 'Troisième couleur', 'Quatrième couleur']
const depuisLien = (typeof route.query.p === 'string' ? route.query.p.split(',') : [])
  .map(h => `#${h.toLowerCase()}`).filter(h => HEXA.test(h)).slice(0, MAX_COULEURS)
const palette = ref<string[]>(depuisLien)
const nom = ref(typeof route.query.nom === 'string' ? route.query.nom.slice(0, 60) : '')
const logo = ref<string | null>(null)
const analyse = ref(false)
const erreur = ref('')

// Un exemple sans marque réelle : croix blanche sur un rond vert, feuille orangée.
const EXEMPLE = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><rect width="120" height="120" fill="#fff"/><circle cx="60" cy="56" r="44" fill="#0f7a6c"/><path d="M52 26h16v22h22v16H68v22H52V64H30V48h22z" fill="#fff"/><path d="M60 112c16-5 28-17 30-34-12 2-23 9-30 20-7-11-18-18-30-20 2 17 14 29 30 34z" fill="#f29d1f"/></svg>')}`

async function lireLogo(source: Blob | string, apercu: string) {
  analyse.value = true
  erreur.value = ''
  try {
    const { couleurs } = await paletteDuLogo(source, MAX_COULEURS)
    logo.value = apercu
    if (!couleurs.length) {
      erreur.value = "Nous n'avons pas trouvé de couleur dans ce logo : choisissez-les ci-dessous."
      palette.value = ['#1f4fa8']
    } else {
      palette.value = couleurs.map(c => c.hex)
    }
  } catch (e) {
    erreur.value = e instanceof Error ? e.message : 'Logo illisible.'
  } finally {
    analyse.value = false
  }
}
function choisirFichier(evenement: Event) {
  const fichier = (evenement.target as HTMLInputElement).files?.[0]
  if (!fichier) return
  if (!fichier.type.startsWith('image/')) {
    erreur.value = 'Choisissez une image (PNG, JPEG, WebP ou SVG).'
    return
  }
  if (fichier.size > 5_000_000) {
    erreur.value = "Ce fichier dépasse 5 Mo : envoyez une version plus légère du logo."
    return
  }
  if (nom.value === NOM_EXEMPLE) nom.value = ''
  const lecteur = new FileReader()
  lecteur.onload = () => void lireLogo(fichier, String(lecteur.result))
  lecteur.readAsDataURL(fichier)
}
const NOM_EXEMPLE = 'Centre de santé (exemple)'
function essayerExemple() {
  if (!nom.value) nom.value = NOM_EXEMPLE
  void lireLogo(EXEMPLE, EXEMPLE)
}
function sansLogo() {
  logo.value = null
  erreur.value = ''
  if (!palette.value.length) palette.value = ['#1f4fa8', '#e07b1f']
}

// Les couleurs vives d'abord : un logo écrit en noir sur fond blanc garde sa couleur de marque
// en principale, le noir ou le gris viennent ensuite.
const ordonnee = computed(() => [...palette.value.filter(h => !estNeutre(h)), ...palette.value.filter(h => estNeutre(h))])
const principale = computed(() => ordonnee.value[0] ?? '#1f4fa8')
const seconde = computed(() => ordonnee.value[1] ?? melanger(principale.value, '#000000', 0.3))
const references = computed(() => palette.value.map(hex => ({ hex, ral: ralLePlusProche(hex) })))

// Les murs : clairs et apaisants, la couleur de marque en soubassement, bandeau et porte.
const MURS = [
  { code: '9010', nom: 'Blanc pur', hex: '#ffffff' },
  { code: '9001', nom: 'Blanc crème', hex: '#fdf4e3' },
  { code: '1015', nom: 'Ivoire clair', hex: '#eadebd' },
  { code: '7035', nom: 'Gris clair', hex: '#cbd0cc' },
]
const murChoisi = ref(typeof route.query.mur === 'string' && /^(\d{4}|claire)$/.test(route.query.mur) ? route.query.mur : '9010')
const teinteClaire = computed(() => ralLePlusProche(melanger(principale.value, '#ffffff', 0.78)))
const mur = computed(() => {
  const fixe = MURS.find(m => m.code === murChoisi.value)
  if (fixe) return { code: `RAL ${fixe.code}`, nom: fixe.nom, hex: fixe.hex }
  return teinteClaire.value
})
const soubassement = computed(() => ralLePlusProche(principale.value))
const porte = computed(() => ralLePlusProche(seconde.value))

// Les tenues : pour chaque rôle, l'article et le coloris du catalogue les plus proches.
interface Candidat { produit: ProduitResume, couleur: string, hex: string, forme: string }
const candidats = computed<Candidat[]>(() => (page.value?.elements ?? []).flatMap((produit) => {
  const forme = formeArticle(produit.rayon_slug, produit.slug)
  if (!forme || !produit.vendable_en_ligne) return []
  return produit.couleurs.filter(c => c.hex).map(c => ({ produit, couleur: c.nom, hex: c.hex!, forme }))
}))
function plusProche(formes: string[], hex: string, brodable = false) {
  return candidats.value
    .filter(c => formes.includes(c.forme) && (!brodable || c.produit.personnalisable))
    .map(c => ({ ...c, ecart: ecart(c.hex, hex) }))
    .sort((a, b) => a.ecart - b.ecart)[0] ?? null
}
type Choisi = NonNullable<ReturnType<typeof plusProche>>
interface Tenue { id: string, titre: string, pour: string, pieces: { role: 'haut' | 'bas' | 'dessus', choisi: Choisi, cible: string }[], logoSur: Choisi }
const tenues = computed<Tenue[]>(() => {
  const liste: Tenue[] = []
  const soins = plusProche(['tunique'], principale.value, true)
  const soinsBas = soins && plusProche(['pantalon', 'pantalon-cargo'], soins.hex)
  if (soins && soinsBas) {
    liste.push({ id: 'soins', titre: 'Soins', pour: 'Infirmiers, sages-femmes, aides-soignants', logoSur: soins, pieces: [
      { role: 'haut', choisi: soins, cible: principale.value }, { role: 'bas', choisi: soinsBas, cible: soins.hex },
    ] })
  }
  const blouse = plusProche(['blouse'], '#ffffff', true)
  const dessous = plusProche(['tunique'], seconde.value)
  const dessousBas = dessous && plusProche(['pantalon', 'pantalon-cargo'], dessous.hex)
  if (blouse && dessous && dessousBas) {
    liste.push({ id: 'medecins', titre: 'Médecins', pour: 'Blouse blanche, logo brodé à vos couleurs', logoSur: blouse, pieces: [
      { role: 'dessus', choisi: blouse, cible: '#ffffff' }, { role: 'haut', choisi: dessous, cible: seconde.value },
      { role: 'bas', choisi: dessousBas, cible: dessous.hex },
    ] })
  }
  const accueil = plusProche(['polo', 'tunique'], seconde.value, true)
  const accueilBas = plusProche(['pantalon', 'pantalon-cargo'], '#1f2a44')
  if (accueil && accueilBas) {
    liste.push({ id: 'accueil', titre: 'Accueil et agents', pour: 'Accueil, caisse, entretien, sécurité', logoSur: accueil, pieces: [
      { role: 'haut', choisi: accueil, cible: seconde.value }, { role: 'bas', choisi: accueilBas, cible: '#1f2a44' },
    ] })
  }
  return liste
})
const habiller = (tenue: Tenue) => Object.fromEntries(
  tenue.pieces.map(p => [p.role, { forme: p.choisi.forme, hex: p.choisi.hex, couleur: p.choisi.couleur } satisfies PieceHabillee]),
)
const prixTenue = (tenue: Tenue) => tenue.pieces.reduce<number | null>(
  (total, p) => (total === null || p.choisi.produit.prix_public === null ? null : total + p.choisi.produit.prix_public), 0,
)

// Partager le rendu (sans le logo, resté sur ce téléphone) et parler du projet.
const SERVICES = [
  { id: 'tenues', texte: "Les tenues de l'équipe à nos couleurs" },
  { id: 'broderie', texte: 'La broderie de notre logo' },
  { id: 'peinture', texte: 'La peinture et la signalétique de nos locaux' },
  { id: 'entretien', texte: "L'entretien de notre linge (tenues, draps, alèses) : collecte, lavage, retour compté" },
]
const voulus = ref<string[]>(['tenues', 'broderie'])
const origine = ref('')
onMounted(() => { origine.value = window.location.origin })
const lienPartage = computed(() => {
  const nomStructure = nom.value.trim() ? `&nom=${encodeURIComponent(nom.value.trim())}` : ''
  return `${origine.value}/a-vos-couleurs?p=${palette.value.map(h => h.slice(1)).join(',')}&mur=${murChoisi.value}${nomStructure}`
})
const messageProjet = computed(() => {
  const couleurs = references.value.map(r => `${r.hex} (${r.ral.code})`).join(', ')
  const besoins = SERVICES.filter(s => voulus.value.includes(s.id)).map(s => `- ${s.texte}`).join('\n')
  return `Bonjour, nous sommes ${nom.value.trim() || 'une structure de santé'}. Nos couleurs : ${couleurs}. Nous voudrions :\n${besoins}\nNotre rendu : ${lienPartage.value}`
})
const whatsapp = computed(() => `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent(messageProjet.value)}`)
const copie = ref(false)
async function copier() {
  try {
    await navigator.clipboard.writeText(lienPartage.value)
    copie.value = true
  } catch {
    copie.value = false
  }
}
watch([palette, nom, murChoisi], () => { copie.value = false }, { deep: true })
</script>

<template>
  <section class="conteneur couleurs-structure">
    <header class="entete">
      <p class="surtitre">Pour les centres de santé, cliniques, pharmacies et écoles</p>
      <h1>Votre structure à vos couleurs</h1>
      <p class="chapeau">
        Déposez votre logo : nous en tirons votre palette, la peinture la plus proche pour vos murs, et votre équipe
        habillée à vos couleurs, logo brodé. Du logo à la blouse, une seule maison.
      </p>
    </header>

    <div class="carte etape">
      <h2><span class="numero">1</span> Votre logo</h2>
      <div class="depot">
        <label class="bouton">
          {{ analyse ? 'Lecture du logo…' : logo ? 'Changer de logo' : 'Choisir le logo' }}
          <input type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" class="visuellement-cache" @change="choisirFichier">
        </label>
        <button type="button" class="bouton bouton-secondaire" @click="essayerExemple">Essayer avec un exemple</button>
        <button v-if="!palette.length" type="button" class="bouton bouton-discret" @click="sansLogo">Je n'ai pas de logo</button>
      </div>
      <p class="aide">Votre logo reste sur votre téléphone : il sert seulement à l'aperçu ci-dessous.</p>
      <p v-if="erreur" class="alerte alerte-info" role="status">{{ erreur }}</p>
      <div class="champ">
        <label for="nom-structure">Nom de la structure (pour l'enseigne)</label>
        <input id="nom-structure" v-model="nom" maxlength="60" placeholder="Centre de santé de…">
      </div>
    </div>

    <template v-if="palette.length">
      <div class="carte etape">
        <h2><span class="numero">2</span> Votre palette</h2>
        <ul class="palette">
          <li v-for="(hex, i) in palette" :key="i">
            <label class="nuance" :style="{ background: hex }">
              <span class="visuellement-cache">{{ ROLES[i] }}</span>
              <input v-model="palette[i]" type="color" class="visuellement-cache">
            </label>
            <div>
              <strong>{{ ROLES[i] }}</strong>
              <span class="code">{{ hex }} · {{ references[i]?.ral.code }} {{ references[i]?.ral.nom }}</span>
              <button v-if="palette.length > 1" type="button" class="retirer" :aria-label="`Retirer la ${ROLES[i]?.toLowerCase()}`" @click="palette.splice(i, 1)">Retirer</button>
            </div>
          </li>
        </ul>
        <button v-if="palette.length < MAX_COULEURS" type="button" class="bouton bouton-discret ajouter" @click="palette.push(melanger(principale, '#ffffff', 0.5))">
          Ajouter une couleur
        </button>
        <p class="aide">Touchez une pastille pour corriger sa couleur.</p>
      </div>

      <div class="carte etape">
        <h2><span class="numero">3</span> Vos murs</h2>
        <div class="murs">
          <FacadeStructure
            :mur="mur.hex" :soubassement="soubassement.hex" :porte="porte.hex" :bandeau="soubassement.hex"
            :logo="logo" :nom="nom" :libelle="`Façade aux couleurs de ${nom || 'votre structure'} : murs ${mur.code}, soubassement ${soubassement.code}, porte ${porte.code}`"
          />
          <div>
            <fieldset class="choix-mur">
              <legend>Couleur des murs</legend>
              <label v-for="m in MURS" :key="m.code" class="puce" :class="{ actif: murChoisi === m.code }">
                <input v-model="murChoisi" type="radio" name="mur" :value="m.code" class="visuellement-cache">
                <span class="echantillon" :style="{ background: m.hex }" aria-hidden="true" />{{ m.nom }}
              </label>
              <label class="puce" :class="{ actif: murChoisi === 'claire' }">
                <input v-model="murChoisi" type="radio" name="mur" value="claire" class="visuellement-cache">
                <span class="echantillon" :style="{ background: teinteClaire.hex }" aria-hidden="true" />Teinte claire de votre couleur
              </label>
            </fieldset>
            <dl class="peintures">
              <div><dt>Murs</dt><dd>{{ mur.code }} {{ mur.nom }}</dd></div>
              <div><dt>Soubassement et bandeau</dt><dd>{{ soubassement.code }} {{ soubassement.nom }} <small>({{ proximite(soubassement.ecart) }})</small></dd></div>
              <div><dt>Porte</dt><dd>{{ porte.code }} {{ porte.nom }} <small>({{ proximite(porte.ecart) }})</small></dd></div>
            </dl>
            <p class="aide">
              Références RAL, reproduites par les magasins de peinture équipés d'une machine à teinter. Vérifiez la
              teinte sur un nuancier imprimé avant de peindre : un écran ne rend jamais tout à fait une peinture.
            </p>
          </div>
        </div>
      </div>

      <div class="carte etape">
        <h2><span class="numero">4</span> Votre équipe</h2>
        <p v-if="!tenues.length" class="aide">Le catalogue se charge…</p>
        <div class="tenues">
          <article v-for="t in tenues" :key="t.id" class="tenue">
            <div class="silhouette">
              <Mannequin v-bind="habiller(t)" :logo="logo" :libelle="`Tenue ${t.titre} aux couleurs de ${nom || 'votre structure'}`" />
            </div>
            <h3>{{ t.titre }}</h3>
            <p class="aide">{{ t.pour }}</p>
            <ul class="pieces">
              <li v-for="p in t.pieces" :key="p.role">
                <span class="echantillon" :style="{ background: p.choisi.hex }" aria-hidden="true" />
                <span><NuxtLink :to="{ path: `/produits/${p.choisi.produit.slug}`, query: { couleur: p.choisi.couleur } }">{{ p.choisi.produit.nom }}</NuxtLink>,
                  {{ p.choisi.couleur.toLowerCase() }}<small v-if="p.cible !== '#ffffff' && p.cible !== '#1f2a44' && p.role !== 'bas'"> ({{ proximite(p.choisi.ecart) }} de votre couleur)</small></span>
              </li>
            </ul>
            <p v-if="prixTenue(t)" class="prix">{{ formaterFcfa(prixTenue(t)!) }} la tenue <small>· logo brodé sur devis</small></p>
            <NuxtLink
              :to="{ path: '/commande-equipe', query: { produit: t.logoSur.produit.slug, couleur: t.logoSur.couleur } }"
              class="bouton bouton-secondaire"
            >
              Habiller l'équipe
            </NuxtLink>
          </article>
        </div>
      </div>

      <div class="carte etape projet">
        <h2><span class="numero">5</span> Votre projet</h2>
        <fieldset>
          <legend>Nous voudrions</legend>
          <label v-for="s in SERVICES" :key="s.id" class="case">
            <input v-model="voulus" type="checkbox" :value="s.id"> {{ s.texte }}
          </label>
        </fieldset>
        <div class="actions">
          <a :href="whatsapp" target="_blank" rel="noopener" class="bouton">En parler sur WhatsApp</a>
          <button type="button" class="bouton bouton-secondaire" @click="copier">{{ copie ? 'Lien copié' : 'Copier le lien du rendu' }}</button>
        </div>
        <p class="aide">Le lien garde la palette, les murs et le nom, pas le logo : partagez-le avec votre direction.</p>
        <p v-if="voulus.includes('entretien')" class="aide">
          L'entretien en détail : <a :href="`${config.public.sitePrestations}/entretien-du-linge`">collecte, lavage par une blanchisserie partenaire, retour compté</a>.
        </p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.couleurs-structure { padding-top: 20px; display: grid; gap: 16px; }
.entete { display: grid; gap: 6px; }
.surtitre { margin: 0; color: var(--primaire); font-weight: 700; font-size: 0.9rem; }
.entete h1 { margin: 0; }
.chapeau { margin: 0; max-width: 62ch; color: var(--texte-doux); }
.etape { padding: 18px; display: grid; gap: 12px; }
.etape h2 { margin: 0; font-size: 1.15rem; display: flex; align-items: center; gap: 10px; }
.numero { display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--primaire); color: #fff; font-size: 0.95rem; flex: none; }
.etape .aide, .etape .alerte { margin: 0; }
.depot { display: flex; flex-wrap: wrap; gap: 8px; }
.depot label.bouton { cursor: pointer; }
.palette { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 230px), 1fr)); }
.palette li { display: flex; align-items: center; gap: 10px; }
.ajouter { justify-self: start; }
.nuance { flex: none; width: 52px; height: 52px; border-radius: 12px; box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.18); cursor: pointer; position: relative; }
.nuance:focus-within { outline: 3px solid var(--primaire); outline-offset: 2px; }
.palette li > div { display: grid; min-width: 0; }
.code { font-size: 0.85rem; color: var(--texte-doux); }
.retirer { justify-self: start; padding: 2px 0; border: 0; background: none; color: var(--primaire); font: inherit; font-size: 0.85rem; text-decoration: underline; cursor: pointer; }
.murs { display: grid; gap: 16px; }
@media (min-width: 820px) { .murs { grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); align-items: start; } }
.choix-mur { border: 0; padding: 0; margin: 0 0 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.choix-mur legend { font-weight: 650; margin-bottom: 6px; }
.puce { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1.5px solid var(--bordure); border-radius: 999px; cursor: pointer; font-size: 0.9rem; }
.puce.actif { border-color: var(--primaire); background: var(--fond-doux, #f3f2fb); font-weight: 650; }
.puce:focus-within { outline: 3px solid var(--primaire); outline-offset: 2px; }
.echantillon { display: inline-block; flex: none; width: 14px; height: 14px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.25); }
.peintures { margin: 0 0 8px; display: grid; gap: 6px; }
.peintures div { display: grid; gap: 1px; }
.peintures dt { font-size: 0.85rem; color: var(--texte-doux); }
.peintures dd { margin: 0; font-weight: 650; }
.peintures small { font-weight: 400; color: var(--texte-doux); }
.tenues { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); }
.tenue { display: grid; gap: 6px; align-content: start; padding: 12px; border: 1px solid var(--bordure); border-radius: 12px; }
.silhouette { height: 270px; background: var(--fond-doux, #f6f5fb); border-radius: 10px; padding: 8px; }
.tenue h3 { margin: 4px 0 0; font-size: 1.05rem; }
.tenue .aide { margin: 0; }
.pieces { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: 0.92rem; }
.pieces li { display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: 8px; align-items: baseline; }
.pieces small { color: var(--texte-doux); }
.prix { margin: 0; font-weight: 700; }
.prix small { font-weight: 400; color: var(--texte-doux); }
.tenue .bouton { justify-self: start; }
.projet fieldset { border: 0; padding: 0; margin: 0; display: grid; gap: 8px; }
.projet legend { font-weight: 650; margin-bottom: 4px; }
.case { display: flex; align-items: flex-start; gap: 10px; }
.case input { flex: none; width: 20px; height: 20px; margin-top: 2px; accent-color: var(--primaire); }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
