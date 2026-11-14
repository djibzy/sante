<script setup lang="ts">
import type { Offre } from '~/types/prestations'

useSeoMeta({
  title: 'Entretien du linge des structures de santé',
  description: 'Tenues, draps, alèses, serviettes : collectés dans votre structure, lavés par une blanchisserie partenaire, rendus propres et comptés pièce par pièce, avec un relevé chaque mois.',
})
const config = useRuntimeConfig()
const { data: offre } = await usePrestationsFetch<Offre>('/api/v1/offre')
const { appeler } = useApiPrestations()
const whatsapp = computed(() => config.public.whatsapp
  ? `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent('Bonjour, je voudrais des informations sur l\'entretien du linge de notre structure.')}`
  : null)

const ETAPES = [
  { titre: 'On compte ensemble', texte: 'À chaque collecte, notre agent compte chaque pièce devant votre personnel. Le compte vous arrive par SMS : c\'est votre bon de collecte.' },
  { titre: 'Lavé chez un partenaire vérifié', texte: 'Une blanchisserie partenaire que nous avons visitée : linge médical lavé à part, à haute température, séché et rangé propre.' },
  { titre: 'Rendu au jour promis', texte: 'Plié, tenues repassées, rendu le jour convenu et recompté devant vous. Une pièce manque ? Elle est signalée aussitôt, recherchée, puis remplacée ou remboursée.' },
  { titre: 'Un relevé chaque mois', texte: 'Bons de collecte, pièces rendues, montant : tout figure sur un relevé simple à vérifier, avant la facture.' },
]

// Estimation des volumes : des hypothèses affichées, modifiables, jamais un prix.
const lits = ref<number | null>(null)
const soignants = ref<number | null>(null)
const changes = ref(3)
const tenueParSoignant = ref(3)
const tenue = ref<'blouse' | 'tunique'>('blouse')
const estimation = computed(() => {
  const l = Math.max(0, lits.value ?? 0)
  const s = Math.max(0, soignants.value ?? 0)
  const volumes: Record<string, number> = {}
  if (l) {
    volumes.drap = l * changes.value * 2
    volumes.taie = l * changes.value
  }
  if (s) {
    const pieces = s * tenueParSoignant.value
    if (tenue.value === 'blouse') volumes.blouse = pieces
    else Object.assign(volumes, { tunique: pieces, pantalon: pieces })
  }
  return volumes
})
const totalEstime = computed(() => Object.values(estimation.value).reduce((a, b) => a + b, 0))

// Demande
const formulaire = reactive({
  structure: '', type_structure: '', contact: '', telephone: '', quartier: '',
  collectes_par_semaine: '' as '' | number, message: '',
})
const volumes = ref<Record<string, number | null>>({})
const envoi = ref(false)
const erreur = ref('')
const recue = ref<{ reference: string; message: string } | null>(null)
const totalDemande = computed(() => Object.values(volumes.value).reduce<number>((a, b) => a + (b ?? 0), 0))

function reporter() {
  volumes.value = { ...volumes.value, ...estimation.value }
  document.getElementById('demande')?.scrollIntoView({ behavior: 'smooth' })
}

async function envoyer() {
  erreur.value = ''
  envoi.value = true
  try {
    recue.value = await appeler<{ reference: string; message: string }>('/api/v1/demandes', {
      method: 'POST',
      body: {
        ...formulaire,
        collectes_par_semaine: formulaire.collectes_par_semaine || null,
        volumes: Object.fromEntries(Object.entries(volumes.value).filter(([, n]) => (n ?? 0) > 0)),
      },
    })
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}
</script>

<template>
  <div class="conteneur linge">
    <section class="ouverture">
      <p class="surtitre">Entretien du linge</p>
      <h1>Le linge de votre structure, propre et compté</h1>
      <p class="chapeau">Tenues, draps, alèses, serviettes, champs : nous les collectons chez vous, une blanchisserie partenaire les lave, nous vous les rendons au jour promis, pièce par pièce.</p>
      <div class="actions">
        <a href="#demande" class="bouton">Demander une visite</a>
        <a v-if="whatsapp" :href="whatsapp" class="bouton bouton-secondaire" target="_blank" rel="noopener">Écrire sur WhatsApp</a>
      </div>
    </section>

    <section aria-labelledby="titre-etapes">
      <h2 id="titre-etapes">Comment ça marche</h2>
      <ol class="etapes">
        <li v-for="(etape, i) in ETAPES" :key="etape.titre" class="carte etape">
          <span class="numero" aria-hidden="true">{{ i + 1 }}</span>
          <h3>{{ etape.titre }}</h3>
          <p>{{ etape.texte }}</p>
        </li>
      </ol>
    </section>

    <section class="deux-colonnes">
      <div>
        <h2>Ce que nous prenons en charge</h2>
        <ul v-if="offre" class="articles">
          <li v-for="article in offre.articles.filter(a => a.code !== 'autre')" :key="article.code">
            <strong>{{ article.libelle }}</strong>
            <span v-if="article.note" class="aide"> – {{ article.note }}</span>
          </li>
          <li>Et le reste de votre linge, à préciser ensemble.</li>
        </ul>
      </div>
      <div class="carte hygiene">
        <h2>Hygiène et confiance</h2>
        <ul>
          <li>Le linge sale voyage en sacs fermés, jamais avec le linge propre.</li>
          <li>Pas d'objet piquant ou coupant ni de déchet de soins dans les sacs : ils restent dans vos circuits de déchets.</li>
          <li>Les champs opératoires sont lavés et pliés ; la stérilisation reste faite par votre structure.</li>
          <li>Aucune information sur vos patients n'est demandée ni enregistrée.</li>
        </ul>
        <p class="aide">Le rythme se fixe avec vous : une, deux ou trois collectes par semaine, ou sur appel.</p>
      </div>
    </section>

    <section class="carte estimer" aria-labelledby="titre-estimer">
      <h2 id="titre-estimer">Estimer vos volumes</h2>
      <p class="aide">Pour préparer la visite : une estimation par semaine, à corriger dans votre demande.</p>
      <div class="grille-estimer">
        <div class="champ">
          <label for="lits">Nombre de lits</label>
          <input id="lits" v-model.number="lits" type="number" inputmode="numeric" min="0" max="2000" placeholder="20">
        </div>
        <div class="champ">
          <label for="changes">Draps changés</label>
          <select id="changes" v-model.number="changes">
            <option :value="2">2 fois par semaine</option>
            <option :value="3">3 fois par semaine</option>
            <option :value="7">Chaque jour</option>
          </select>
        </div>
        <div class="champ">
          <label for="soignants">Soignants en tenue</label>
          <input id="soignants" v-model.number="soignants" type="number" inputmode="numeric" min="0" max="2000" placeholder="12">
        </div>
        <div class="champ">
          <label for="tenue">Tenue portée</label>
          <select id="tenue" v-model="tenue">
            <option value="blouse">Blouse</option>
            <option value="tunique">Tunique et pantalon</option>
          </select>
        </div>
        <div class="champ">
          <label for="par-soignant">Tenues par soignant</label>
          <select id="par-soignant" v-model.number="tenueParSoignant">
            <option :value="2">2 par semaine</option>
            <option :value="3">3 par semaine</option>
            <option :value="5">5 par semaine</option>
          </select>
        </div>
      </div>
      <div v-if="totalEstime" class="resultat" aria-live="polite">
        <p><strong>Environ {{ totalEstime }} pièces par semaine</strong></p>
        <p class="aide">
          <template v-for="(n, code, i) in estimation" :key="code">{{ i ? ', ' : '' }}{{ n }} {{ offre?.articles.find(a => a.code === code)?.pluriel ?? code }}</template>.
          Hypothèses : deux draps et une taie par lit à chaque change.
        </p>
        <button type="button" class="bouton bouton-secondaire" @click="reporter">Reporter dans ma demande</button>
      </div>
    </section>

    <section id="demande" class="carte demande" aria-labelledby="titre-demande">
      <template v-if="recue">
        <h2 id="titre-demande">Demande envoyée</h2>
        <div class="alerte alerte-succes" role="status">
          <strong>{{ recue.reference }}</strong> – {{ recue.message }}
        </div>
        <p>Un SMS de confirmation part vers votre numéro. Gardez la référence pour en parler avec nous.</p>
      </template>
      <template v-else>
        <h2 id="titre-demande">Demander une visite</h2>
        <p class="aide">Nous vous rappelons pour visiter votre structure, voir votre linge et vous proposer un rythme et un prix.</p>
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <form @submit.prevent="envoyer">
          <div class="grille-formulaire">
            <div class="champ">
              <label for="structure">Nom de la structure</label>
              <input id="structure" v-model="formulaire.structure" required minlength="2" maxlength="160" autocomplete="organization">
            </div>
            <div class="champ">
              <label for="type">Type de structure</label>
              <select id="type" v-model="formulaire.type_structure" required>
                <option value="" disabled>Choisir…</option>
                <option v-for="t in offre?.types_structure ?? []" :key="t.code" :value="t.code">{{ t.libelle }}</option>
              </select>
            </div>
            <div class="champ">
              <label for="contact">Votre nom et votre fonction</label>
              <input id="contact" v-model="formulaire.contact" required minlength="2" maxlength="120" placeholder="Awa Traoré, surveillante générale" autocomplete="name">
            </div>
            <div class="champ">
              <label for="telephone">Téléphone</label>
              <input id="telephone" v-model="formulaire.telephone" type="tel" inputmode="tel" required autocomplete="tel" placeholder="76 12 34 56">
            </div>
            <div class="champ">
              <label for="quartier">Quartier et ville</label>
              <input id="quartier" v-model="formulaire.quartier" required minlength="2" maxlength="160" placeholder="Badalabougou, Bamako">
            </div>
            <div class="champ">
              <label for="rythme">Collectes souhaitées</label>
              <select id="rythme" v-model="formulaire.collectes_par_semaine">
                <option value="">À voir ensemble</option>
                <option :value="1">Une par semaine</option>
                <option :value="2">Deux par semaine</option>
                <option :value="3">Trois par semaine</option>
                <option :value="6">Chaque jour (sauf dimanche)</option>
              </select>
            </div>
          </div>
          <details class="volumes" :open="totalDemande > 0">
            <summary>Volumes par semaine <span class="aide">(facultatif{{ totalDemande ? ` : ${totalDemande} pièces` : '' }})</span></summary>
            <GrilleArticles v-if="offre" v-model="volumes" :articles="offre.articles.filter(a => a.code !== 'autre')" identifiant="volume" :avec-precision="false" />
          </details>
          <div class="champ">
            <label for="message">Message <span class="aide">(facultatif)</span></label>
            <textarea id="message" v-model="formulaire.message" maxlength="1000" placeholder="Horaires de passage, accès, questions…" />
            <p class="aide">Ne mentionnez aucune information sur vos patients.</p>
          </div>
          <button type="submit" class="bouton" :disabled="envoi">Envoyer la demande</button>
        </form>
      </template>
    </section>

    <p class="aide autres">
      Vous habillez votre équipe ? Les tenues brodées à votre logo sont chez
      <a :href="`${config.public.siteBoutique}/commande-equipe`">Bibou, notre boutique</a> ;
      l'entretien les garde belles plus longtemps.
    </p>
  </div>
</template>

<style scoped>
.linge { display: grid; gap: 28px; }
.ouverture { max-width: 780px; padding-top: 12px; }
.surtitre { color: var(--primaire); font-weight: 700; margin-bottom: 0.4em; }
.chapeau { font-size: 1.15rem; color: var(--texte-doux); }
.actions { display: flex; gap: 10px; flex-wrap: wrap; }
h2 { margin-top: 0; }
.etapes { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); }
.etape { padding: 18px; }
.etape h3 { margin: 8px 0 6px; font-size: 1.08rem; }
.etape p { margin: 0; color: var(--texte-doux); }
.numero { display: inline-grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--primaire); color: #fff; font-weight: 800; }
.deux-colonnes { display: grid; gap: 20px; }
@media (min-width: 860px) { .deux-colonnes { grid-template-columns: 1fr 1fr; align-items: start; } }
.articles { margin: 0; padding-left: 1.2em; display: grid; gap: 4px; }
.hygiene { padding: 20px; background: var(--primaire-clair); border-color: transparent; }
.hygiene ul { margin: 0 0 12px; padding-left: 1.2em; display: grid; gap: 6px; }
.estimer, .demande { padding: 20px; }
.grille-estimer, .grille-formulaire { display: grid; gap: 0 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); }
.resultat { border-top: 1px solid var(--bordure); padding-top: 12px; }
.resultat p { margin: 0 0 8px; }
.volumes { margin: 4px 0 16px; }
.volumes summary { cursor: pointer; font-weight: 650; padding: 6px 0 10px; }
.autres { margin: 0; }
</style>
