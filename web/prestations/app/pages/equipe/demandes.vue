<script setup lang="ts">
import type { Demande, Offre, PageDemandes, StatutDemande } from '~/types/prestations'

// Demandes reçues de la page publique : rappeler, noter, signer un contrat ou classer.
useSeoMeta({ title: 'Demandes', robots: 'noindex' })
const ONGLETS: { cle: string; titre: string; statuts: StatutDemande[] }[] = [
  { cle: 'nouvelles', titre: 'Nouvelles', statuts: ['nouvelle'] },
  { cle: 'discussion', titre: 'En discussion', statuts: ['en_discussion'] },
  { cle: 'signees', titre: 'Signées', statuts: ['signee'] },
  { cle: 'sans-suite', titre: 'Sans suite', statuts: ['sans_suite'] },
  { cle: 'toutes', titre: 'Toutes', statuts: [] },
]
const route = useRoute()
const { appeler } = useApiPrestations()
const { verifie, estGestionnaire } = useEquipe()
const onglet = computed(() => ONGLETS.find(o => o.cle === route.query.onglet) ?? ONGLETS[0]!)
const page = ref<PageDemandes | null>(null)
const offre = ref<Offre | null>(null)
const notes = ref<Record<string, string>>({})
const erreur = ref('')
const message = ref('')

const pluriel = (code: string) => offre.value?.articles.find(a => a.code === code)?.pluriel ?? code

async function charger() {
  if (!estGestionnaire.value) return
  try {
    ;[page.value, offre.value] = await Promise.all([
      appeler<PageDemandes>('/api/v1/admin/demandes', { query: { statut: onglet.value.statuts } }),
      offre.value ?? appeler<Offre>('/api/v1/offre'),
    ])
    notes.value = Object.fromEntries(page.value.elements.map(d => [d.id, d.notes_equipe]))
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function modifier(demande: Demande, changements: { statut?: StatutDemande; notes_equipe?: string }) {
  try {
    const modifiee = await appeler<Demande>(`/api/v1/admin/demandes/${demande.reference}`, {
      method: 'PATCH', body: changements,
    })
    message.value = `${modifiee.reference} : ${modifiee.libelle_statut.toLowerCase()}, notes enregistrées.`
    erreur.value = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}
watch([verifie, () => route.query.onglet], charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe gestion>
      <div class="entete-page">
        <h1>Demandes</h1>
        <span v-if="page" class="aide">{{ page.nouvelles }} nouvelle(s) à rappeler</span>
      </div>
      <nav class="onglets" aria-label="Filtrer les demandes">
        <NuxtLink v-for="o in ONGLETS" :key="o.cle" :to="{ query: { onglet: o.cle } }" :class="{ actif: o.cle === onglet.cle }">{{ o.titre }}</NuxtLink>
      </nav>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>
      <p v-if="page && !page.elements.length" class="aide">Aucune demande ici.</p>
      <div class="liste-cartes">
        <article v-for="d in page?.elements ?? []" :key="d.id" class="carte demande">
          <header>
            <div>
              <h2>{{ d.structure }}</h2>
              <p class="aide">{{ d.reference }} · {{ d.libelle_type }} · {{ d.quartier }} · reçue le {{ formaterDateHeure(d.cree_le) }}</p>
            </div>
            <span class="pastille" :class="{ 'pastille-accent': d.statut === 'nouvelle', 'pastille-succes': d.statut === 'signee', 'pastille-attente': d.statut === 'sans_suite' }">{{ d.libelle_statut }}</span>
          </header>
          <p>{{ d.contact }} · <a :href="`tel:${d.telephone}`">{{ formaterTelephone(d.telephone) }}</a></p>
          <p v-if="d.pieces_par_semaine" class="aide">
            {{ d.pieces_par_semaine }} pièces par semaine :
            <template v-for="(n, code, i) in d.volumes" :key="code">{{ i ? ', ' : '' }}{{ n }} {{ pluriel(String(code)) }}</template>
            <template v-if="d.collectes_par_semaine"> · {{ d.collectes_par_semaine }} collecte(s) par semaine souhaitée(s)</template>
          </p>
          <blockquote v-if="d.message">{{ d.message }}</blockquote>
          <div class="champ">
            <label :for="`notes-${d.id}`">Notes de l'équipe</label>
            <textarea :id="`notes-${d.id}`" v-model="notes[d.id]" rows="2" maxlength="2000" placeholder="Appel, visite prévue, besoins…" />
          </div>
          <div class="boutons">
            <button type="button" class="bouton bouton-secondaire" @click="modifier(d, { notes_equipe: notes[d.id] ?? '' })">Enregistrer les notes</button>
            <template v-if="d.statut !== 'signee'">
              <button v-if="d.statut !== 'en_discussion'" type="button" class="bouton bouton-secondaire" @click="modifier(d, { statut: 'en_discussion', notes_equipe: notes[d.id] ?? '' })">En discussion</button>
              <NuxtLink :to="{ path: '/equipe/contrats/nouveau', query: { demande: d.reference } }" class="bouton">Signer le contrat</NuxtLink>
              <button v-if="d.statut !== 'sans_suite'" type="button" class="bouton bouton-discret" @click="modifier(d, { statut: 'sans_suite', notes_equipe: notes[d.id] ?? '' })">Sans suite</button>
            </template>
            <NuxtLink v-else-if="d.contrat_reference" :to="`/equipe/contrats/${d.contrat_reference}`">Contrat {{ d.contrat_reference }}</NuxtLink>
          </div>
        </article>
      </div>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.demande { padding: 16px; display: grid; gap: 6px; }
.demande header { display: flex; justify-content: space-between; gap: 10px; align-items: start; }
.demande h2 { margin: 0; font-size: 1.15rem; }
.demande p { margin: 0; }
blockquote { margin: 4px 0; padding: 8px 12px; border-left: 3px solid var(--primaire); background: var(--fond-doux); border-radius: 0 8px 8px 0; }
</style>
