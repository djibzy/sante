<script setup lang="ts">
import type { Contrat, Demande, Offre, PageCollectes, Partenaire } from '~/types/prestations'
import { classeCollecte } from '~/types/prestations'

// Un contrat : calendrier de collecte, partenaire, formule et tarifs. « nouveau » : la page
// de signature, préremplie depuis une demande (?demande=DE-101).
useSeoMeta({ title: 'Contrat', robots: 'noindex' })
const route = useRoute()
const { appeler, telecharger } = useApiPrestations()
const { verifie, estGestionnaire } = useEquipe()
const reference = computed(() => String(route.params.reference))
const nouveau = computed(() => reference.value === 'nouveau')

const TYPES_STRUCTURE = ref<Offre['types_structure']>([])
const offre = ref<Offre | null>(null)
const partenaires = ref<Partenaire[]>([])
const contrat = ref<Contrat | null>(null)
const demande = ref<Demande | null>(null)
const collectes = ref<PageCollectes | null>(null)
const erreur = ref('')
const message = ref('')
const envoi = ref(false)
const mois = ref(moisCourant())

const fiche = reactive({
  statut: 'actif', structure: '', type_structure: '', contact: '', telephone: '', adresse: '',
  partenaire_id: '' as string, jours_collecte: [] as number[], delai_retour_jours: 3,
  formule: 'piece' as 'piece' | 'forfait', forfait_mensuel: null as number | null,
  pieces_incluses: null as number | null, prix_piece_supplementaire: null as number | null,
  sms_actifs: true, debut_le: aujourdHui(), fin_le: '' as string, notes: '',
})
const tarifs = ref<Record<string, number | null>>({})

function remplir(c: Contrat) {
  Object.assign(fiche, {
    statut: c.statut, structure: c.structure, type_structure: c.type_structure, contact: c.contact,
    telephone: c.telephone, adresse: c.adresse, partenaire_id: c.partenaire?.id ?? '',
    jours_collecte: [...c.jours_collecte], delai_retour_jours: c.delai_retour_jours, formule: c.formule,
    forfait_mensuel: c.forfait_mensuel, pieces_incluses: c.pieces_incluses,
    prix_piece_supplementaire: c.prix_piece_supplementaire, sms_actifs: c.sms_actifs,
    debut_le: c.debut_le, fin_le: c.fin_le ?? '', notes: c.notes,
  })
  tarifs.value = { ...c.tarifs }
}

async function charger() {
  if (!estGestionnaire.value) return
  try {
    ;[offre.value, partenaires.value] = await Promise.all([
      appeler<Offre>('/api/v1/offre'),
      appeler<Partenaire[]>('/api/v1/admin/partenaires'),
    ])
    TYPES_STRUCTURE.value = offre.value.types_structure
    if (nouveau.value) {
      if (typeof route.query.demande === 'string') {
        demande.value = await appeler<Demande>(`/api/v1/admin/demandes/${route.query.demande}`)
        Object.assign(fiche, {
          structure: demande.value.structure, type_structure: demande.value.type_structure,
          contact: demande.value.contact, telephone: demande.value.telephone, adresse: demande.value.quartier,
        })
      }
      return
    }
    contrat.value = await appeler<Contrat>(`/api/v1/admin/contrats/${reference.value}`)
    remplir(contrat.value)
    collectes.value = await appeler<PageCollectes>('/api/v1/admin/collectes', {
      query: { contrat: contrat.value.reference, par_page: 10 },
    })
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function enregistrer() {
  erreur.value = ''
  message.value = ''
  envoi.value = true
  const corps: Record<string, unknown> = {
    ...fiche,
    partenaire_id: fiche.partenaire_id || null,
    fin_le: fiche.fin_le || null,
    tarifs: Object.fromEntries(Object.entries(tarifs.value).filter(([, prix]) => prix !== null && prix !== undefined)),
  }
  try {
    if (nouveau.value) {
      delete corps.statut
      const cree = await appeler<Contrat>('/api/v1/admin/contrats', {
        method: 'POST', body: { ...corps, demande_id: demande.value?.id ?? null },
      })
      await navigateTo(`/equipe/contrats/${cree.reference}`)
      return
    }
    contrat.value = await appeler<Contrat>(`/api/v1/admin/contrats/${reference.value}`, { method: 'PATCH', body: corps })
    remplir(contrat.value)
    message.value = 'Contrat enregistré.'
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function releve() {
  try {
    await telecharger(`/api/v1/admin/contrats/${reference.value}/releves/${mois.value}.pdf`, `releve-${reference.value}-${mois.value}.pdf`)
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}
watch([verifie, reference], charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe gestion>
      <div class="entete-page">
        <h1>{{ nouveau ? 'Nouveau contrat' : `Contrat ${reference}` }}</h1>
        <NuxtLink to="/equipe/contrats">Tous les contrats</NuxtLink>
      </div>
      <p v-if="demande" class="alerte alerte-info">Signature de la demande {{ demande.reference }} : {{ demande.pieces_par_semaine }} pièces par semaine annoncées. {{ demande.message }}</p>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>

      <form v-if="offre" class="carte fiche" @submit.prevent="enregistrer">
        <fieldset>
          <legend>La structure</legend>
          <div class="grille-champs">
            <div class="champ"><label for="structure">Nom</label><input id="structure" v-model="fiche.structure" required minlength="2" maxlength="160"></div>
            <div class="champ">
              <label for="type">Type</label>
              <select id="type" v-model="fiche.type_structure" required>
                <option value="" disabled>Choisir…</option>
                <option v-for="t in TYPES_STRUCTURE" :key="t.code" :value="t.code">{{ t.libelle }}</option>
              </select>
            </div>
            <div class="champ"><label for="contact">Contact (nom, fonction)</label><input id="contact" v-model="fiche.contact" required minlength="2" maxlength="120"></div>
            <div class="champ"><label for="telephone">Téléphone (reçoit les SMS)</label><input id="telephone" v-model="fiche.telephone" type="tel" required></div>
          </div>
          <div class="champ"><label for="adresse">Lieu de collecte (quartier, rue, repère, à qui s'adresser)</label><input id="adresse" v-model="fiche.adresse" required minlength="5" maxlength="300"></div>
        </fieldset>

        <fieldset>
          <legend>Le rythme</legend>
          <p class="aide">Aucun jour coché : collectes sur appel seulement.</p>
          <div class="jours">
            <label v-for="(nom, i) in JOURS" :key="nom" class="jour">
              <input v-model="fiche.jours_collecte" type="checkbox" :value="i + 1"> {{ nom }}
            </label>
          </div>
          <div class="grille-champs">
            <div class="champ"><label for="delai">Retour promis (jours, dimanche exclu)</label><input id="delai" v-model.number="fiche.delai_retour_jours" type="number" min="1" max="14" required></div>
            <div class="champ">
              <label for="partenaire">Partenaire par défaut</label>
              <select id="partenaire" v-model="fiche.partenaire_id">
                <option value="">À choisir au dépôt</option>
                <option v-for="p in partenaires.filter(x => x.est_actif || x.id === fiche.partenaire_id)" :key="p.id" :value="p.id">{{ p.nom }}</option>
              </select>
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Le prix</legend>
          <div class="formules">
            <label><input v-model="fiche.formule" type="radio" value="piece"> À la pièce rendue</label>
            <label><input v-model="fiche.formule" type="radio" value="forfait"> Forfait mensuel</label>
          </div>
          <div v-if="fiche.formule === 'forfait'" class="grille-champs">
            <div class="champ"><label for="forfait">Forfait par mois (FCFA)</label><input id="forfait" v-model.number="fiche.forfait_mensuel" type="number" min="0" step="500" required></div>
            <div class="champ"><label for="incluses">Pièces comprises par mois <span class="aide">(vide : sans limite)</span></label><input id="incluses" v-model.number="fiche.pieces_incluses" type="number" min="0"></div>
            <div class="champ"><label for="supplement">Prix d'une pièce au-delà (FCFA)</label><input id="supplement" v-model.number="fiche.prix_piece_supplementaire" type="number" min="0" step="25"></div>
          </div>
          <template v-else>
            <p class="aide">Prix par pièce rendue. Un article sans prix est signalé « à fixer » sur le relevé.</p>
            <GrilleArticles v-model="tarifs" :articles="offre.articles" mode="prix" identifiant="tarif" :avec-precision="false" />
          </template>
        </fieldset>

        <fieldset>
          <legend>Le contrat</legend>
          <div class="grille-champs">
            <div class="champ"><label for="debut">Début</label><input id="debut" v-model="fiche.debut_le" type="date" required></div>
            <div class="champ"><label for="fin">Fin <span class="aide">(facultatif)</span></label><input id="fin" v-model="fiche.fin_le" type="date"></div>
            <div v-if="!nouveau" class="champ">
              <label for="statut">Statut</label>
              <select id="statut" v-model="fiche.statut">
                <option value="actif">Actif</option>
                <option value="suspendu">Suspendu (plus de collecte au calendrier)</option>
                <option value="termine">Terminé</option>
              </select>
            </div>
          </div>
          <label class="case"><input v-model="fiche.sms_actifs" type="checkbox"> SMS de bon de collecte à la structure</label>
          <div class="champ"><label for="notes">Notes</label><textarea id="notes" v-model="fiche.notes" rows="2" maxlength="2000" /></div>
        </fieldset>
        <button type="submit" class="bouton" :disabled="envoi">{{ nouveau ? 'Signer le contrat' : 'Enregistrer' }}</button>
      </form>

      <section v-if="contrat" class="carte annexe">
        <h2>Relevé mensuel</h2>
        <div class="boutons">
          <label for="mois" class="visuellement-cache">Mois</label>
          <input id="mois" v-model="mois" type="month">
          <button type="button" class="bouton bouton-secondaire" @click="releve">Télécharger le relevé (PDF)</button>
        </div>
        <h2>Dernières collectes</h2>
        <p v-if="!collectes?.elements.length" class="aide">Aucune collecte pour l'instant.</p>
        <ul class="collectes">
          <li v-for="c in collectes?.elements ?? []" :key="c.id">
            <NuxtLink :to="`/equipe/collectes/${c.reference}`">{{ c.reference }}</NuxtLink>
            {{ formaterDate(c.prevue_le) }} · {{ c.pieces_enlevees }} pièces
            <span :class="classeCollecte(c.statut, c.en_retard)">{{ c.en_retard ? 'En retard' : c.libelle_statut }}</span>
          </li>
        </ul>
      </section>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.fiche { padding: 20px; display: grid; gap: 16px; }
.fiche fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.fiche legend { font-weight: 800; font-size: 1.1rem; margin-bottom: 6px; }
.jours, .formules { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-bottom: 10px; }
.jour, .formules label, .case { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; min-height: 36px; }
.jour input, .formules input, .case input { width: 20px; height: 20px; }
.case { margin-bottom: 10px; }
.annexe { padding: 20px; margin-top: 16px; }
.annexe h2 { margin: 0 0 10px; font-size: 1.15rem; }
.annexe .boutons { margin-bottom: 18px; }
.annexe input[type="month"] { min-height: 46px; border: 1.5px solid var(--bordure); border-radius: 10px; padding: 0 0.6em; font: inherit; }
.collectes { margin: 0; padding-left: 1.1em; display: grid; gap: 6px; }
</style>
