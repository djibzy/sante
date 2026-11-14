<script setup lang="ts">
import type { Collecte, Offre, PartenaireResume, Passage, Tournee } from '~/types/prestations'
import { classeCollecte } from '~/types/prestations'

// La tournée d'un jour, dans l'ordre du terrain : les structures à visiter, le linge à déposer
// chez les partenaires, le linge propre à rendre.
useSeoMeta({ title: 'Tournée', robots: 'noindex' })
const route = useRoute()
const router = useRouter()
const { appeler } = useApiPrestations()
const { verifie, autorise } = useEquipe()
const jour = computed(() => (typeof route.query.jour === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(route.query.jour)
  ? route.query.jour
  : aujourdHui()))
const tournee = ref<Tournee | null>(null)
const offre = ref<Offre | null>(null)
const partenaires = ref<PartenaireResume[]>([])
const erreur = ref('')
const message = ref('')
const ouvert = ref<string | null>(null) // formulaire ouvert : « enlever-CT-101 », « rendre-BC-1001 »…
const motif = ref('')

async function charger() {
  if (!autorise.value) return
  try {
    const [t, o, p] = await Promise.all([
      appeler<Tournee>('/api/v1/tournee', { query: { jour: jour.value } }),
      offre.value ?? appeler<Offre>('/api/v1/offre'),
      partenaires.value.length ? partenaires.value : appeler<PartenaireResume[]>('/api/v1/partenaires'),
    ])
    tournee.value = t
    offre.value = o
    partenaires.value = p
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function changerJour(nouveau: string) {
  ouvert.value = null
  void router.replace({ query: { ...route.query, jour: nouveau === aujourdHui() ? undefined : nouveau } })
}

async function apres(collecte: Collecte, texte: string) {
  ouvert.value = null
  message.value = `${collecte.reference} : ${texte}`
  await charger()
}

async function annulerPassage(passage: Passage) {
  try {
    await appeler<Collecte>('/api/v1/tournee/annulations', {
      method: 'POST', body: { contrat_id: passage.contrat.id, jour: jour.value, motif: motif.value },
    })
    motif.value = ''
    ouvert.value = null
    message.value = `${passage.contrat.structure} : passage annulé.`
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function prete(collecte: Collecte) {
  try {
    await apres(await appeler<Collecte>(`/api/v1/collectes/${collecte.reference}/prete`, { method: 'POST' }), 'prête chez le partenaire.')
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

const aFaire = (p: Passage) => !p.collecte || p.collecte.statut === 'prevue'
watch([verifie, jour], charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe>
      <div class="entete-page">
        <h1>Tournée <span v-if="tournee" class="aide">{{ tournee.libelle_jour }}</span></h1>
        <div class="boutons navigation-jour">
          <button type="button" class="bouton bouton-secondaire" aria-label="Jour précédent" @click="changerJour(decaler(jour, -1))">‹</button>
          <label for="jour" class="visuellement-cache">Jour de la tournée</label>
          <input id="jour" type="date" :value="jour" @change="changerJour(($event.target as HTMLInputElement).value || aujourdHui())">
          <button type="button" class="bouton bouton-secondaire" aria-label="Jour suivant" @click="changerJour(decaler(jour, 1))">›</button>
        </div>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>

      <template v-if="tournee && offre">
        <h2 id="passages">Passages <span class="aide">({{ tournee.passages.filter(aFaire).length }} à faire)</span></h2>
        <p v-if="!tournee.passages.length" class="aide">Aucune structure à visiter ce jour-là.</p>
        <div class="liste-cartes">
          <article v-for="passage in tournee.passages" :key="passage.contrat.id" class="carte passage">
            <header>
              <div>
                <h3>{{ passage.contrat.structure }}</h3>
                <p class="aide">{{ passage.contrat.adresse }}</p>
              </div>
              <span v-if="passage.collecte" :class="classeCollecte(passage.collecte.statut)">{{ passage.collecte.libelle_statut }}</span>
              <span v-else class="pastille pastille-attente">À enlever</span>
            </header>
            <p class="contact">
              {{ passage.contrat.contact }} ·
              <a :href="`tel:${passage.contrat.telephone}`">{{ formaterTelephone(passage.contrat.telephone) }}</a>
              <span v-if="!passage.au_calendrier" class="pastille pastille-accent">Collecte demandée</span>
            </p>
            <p v-if="passage.collecte?.statut === 'annulee'" class="aide">Annulé : {{ passage.collecte.motif_annulation }}</p>
            <p v-else-if="passage.collecte && !aFaire(passage)" class="aide">
              <NuxtLink :to="`/equipe/collectes/${passage.collecte.reference}`">{{ passage.collecte.reference }}</NuxtLink> :
              {{ passage.collecte.pieces_enlevees }} pièces enlevées, remises par {{ passage.collecte.remis_par }}.
            </p>

            <div v-if="aFaire(passage) || passage.collecte?.statut === 'enlevee' || passage.collecte?.statut === 'annulee'" class="boutons">
              <button
                v-if="ouvert !== `enlever-${passage.contrat.reference}`" type="button" class="bouton"
                @click="ouvert = `enlever-${passage.contrat.reference}`"
              >
                {{ passage.collecte?.statut === 'enlevee' ? 'Recompter' : 'Enlever le linge' }}
              </button>
              <button
                v-if="aFaire(passage) && ouvert !== `annuler-${passage.contrat.reference}`" type="button" class="bouton bouton-secondaire"
                @click="ouvert = `annuler-${passage.contrat.reference}`"
              >
                Rien à collecter
              </button>
            </div>
            <FormulaireEnlevement
              v-if="ouvert === `enlever-${passage.contrat.reference}`"
              :contrat="passage.contrat" :jour="jour" :articles="offre.articles"
              :collecte="passage.collecte?.statut === 'enlevee' ? passage.collecte : null"
              @fait="c => apres(c, `${c.pieces_enlevees} pièces enlevées, SMS envoyé à la structure.`)"
              @fermer="ouvert = null"
            />
            <form v-if="ouvert === `annuler-${passage.contrat.reference}`" class="formulaire-terrain" @submit.prevent="annulerPassage(passage)">
              <div class="champ">
                <label :for="`motif-${passage.contrat.reference}`">Pourquoi ?</label>
                <input :id="`motif-${passage.contrat.reference}`" v-model="motif" required minlength="3" maxlength="200" placeholder="Structure fermée, linge pas prêt…">
              </div>
              <div class="boutons">
                <button type="submit" class="bouton">Annuler ce passage</button>
                <button type="button" class="bouton bouton-discret" @click="ouvert = null">Fermer</button>
              </div>
            </form>
          </article>
        </div>

        <h2 id="a-deposer">À déposer chez un partenaire</h2>
        <p v-if="!tournee.a_deposer.length" class="aide">Rien à déposer.</p>
        <div class="liste-cartes">
          <CarteCollecte v-for="c in tournee.a_deposer" :key="c.id" :collecte="c">
            <FormulaireDepot :collecte="c" :partenaires="partenaires" @fait="d => apres(d, `déposée chez ${d.partenaire?.nom}.`)" />
          </CarteCollecte>
        </div>

        <h2 id="a-rendre">À rendre</h2>
        <p v-if="!tournee.a_rendre.length" class="aide">Rien à rendre.</p>
        <div class="liste-cartes">
          <CarteCollecte v-for="c in tournee.a_rendre" :key="c.id" :collecte="c">
            <p class="aide">Partenaire : {{ c.partenaire?.nom }}<template v-if="c.partenaire"> · <a :href="`tel:${c.partenaire.telephone}`">{{ formaterTelephone(c.partenaire.telephone) }}</a></template></p>
            <div v-if="ouvert !== `rendre-${c.reference}`" class="boutons">
              <button type="button" class="bouton" @click="ouvert = `rendre-${c.reference}`">Rendre et recompter</button>
              <button v-if="c.statut === 'chez_partenaire'" type="button" class="bouton bouton-secondaire" @click="prete(c)">Prête chez le partenaire</button>
            </div>
            <FormulaireRetour
              v-else :collecte="c"
              @fait="r => apres(r, r.pieces_manquantes ? `rendue, ${r.pieces_manquantes} pièce(s) manquante(s) signalée(s).` : 'rendue, toutes les pièces sont là.')"
              @fermer="ouvert = null"
            />
          </CarteCollecte>
        </div>
      </template>
    </AccesEquipe>
  </section>
</template>

<style scoped>
h1 .aide { font-size: 1rem; font-weight: 500; }
h2 { font-size: 1.2rem; margin-top: 1.6rem; }
.navigation-jour input { min-height: 46px; border: 1.5px solid var(--bordure); border-radius: 10px; padding: 0 0.6em; font: inherit; }
.navigation-jour .bouton { padding: 0 1em; font-size: 1.2rem; }
.passage { padding: 14px 16px; display: grid; gap: 6px; }
.passage header { display: flex; justify-content: space-between; gap: 10px; align-items: start; }
.passage h3 { margin: 0; font-size: 1.1rem; }
.passage p { margin: 0; }
.contact { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
</style>
