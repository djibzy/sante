<script setup lang="ts">
import type { PageDemandes, Synthese, Tournee } from '~/types/prestations'

useSeoMeta({ title: 'Aujourd\'hui', robots: 'noindex' })
const { appeler } = useApiPrestations()
const { verifie, autorise, estGestionnaire, utilisateur } = useEquipe()
const tournee = ref<Tournee | null>(null)
const demandes = ref<PageDemandes | null>(null)
const synthese = ref<Synthese | null>(null)
const erreur = ref('')

const aEnlever = computed(() => (tournee.value?.passages ?? [])
  .filter(p => !p.collecte || p.collecte.statut === 'prevue').length)
const retards = computed(() => (tournee.value?.a_rendre ?? []).filter(c => c.en_retard).length)

async function charger() {
  if (!autorise.value) return
  try {
    tournee.value = await appeler<Tournee>('/api/v1/tournee')
    if (estGestionnaire.value) {
      ;[demandes.value, synthese.value] = await Promise.all([
        appeler<PageDemandes>('/api/v1/admin/demandes', { query: { statut: 'nouvelle' } }),
        appeler<Synthese>(`/api/v1/admin/releves/${moisCourant()}`),
      ])
    }
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}
watch(verifie, charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe>
      <h1>Bonjour {{ utilisateur?.nom?.split(' ')[0] }}</h1>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="tournee" class="tuiles">
        <NuxtLink to="/equipe/tournee" class="carte tuile">
          <span class="chiffre">{{ aEnlever }}</span>
          <span>passage{{ aEnlever > 1 ? 's' : '' }} à faire aujourd'hui</span>
        </NuxtLink>
        <NuxtLink to="/equipe/tournee#a-deposer" class="carte tuile">
          <span class="chiffre">{{ tournee.a_deposer.length }}</span>
          <span>collecte{{ tournee.a_deposer.length > 1 ? 's' : '' }} à déposer chez un partenaire</span>
        </NuxtLink>
        <NuxtLink to="/equipe/tournee#a-rendre" class="carte tuile" :class="{ alerte: retards }">
          <span class="chiffre">{{ tournee.a_rendre.length }}</span>
          <span>à rendre<template v-if="retards">, dont {{ retards }} en retard</template></span>
        </NuxtLink>
        <NuxtLink v-if="demandes" to="/equipe/demandes" class="carte tuile">
          <span class="chiffre">{{ demandes.nouvelles }}</span>
          <span>nouvelle{{ demandes.nouvelles > 1 ? 's' : '' }} demande{{ demandes.nouvelles > 1 ? 's' : '' }} à rappeler</span>
        </NuxtLink>
      </div>
      <div v-if="synthese" class="carte mois">
        <h2>{{ synthese.libelle_mois }}, à ce jour</h2>
        <dl>
          <div><dt>Montant dû par les structures</dt><dd>{{ formaterFcfa(synthese.chiffre) }}</dd></div>
          <div><dt>Coût des partenaires</dt><dd>{{ formaterFcfa(synthese.cout) }}</dd></div>
          <div><dt>Marge</dt><dd>{{ formaterFcfa(synthese.marge) }}</dd></div>
          <div><dt>Pièces sorties, pas encore rendues</dt><dd>{{ synthese.en_cours }}</dd></div>
        </dl>
        <NuxtLink to="/equipe/releves">Voir les relevés</NuxtLink>
      </div>
    </AccesEquipe>
  </section>
</template>

<style scoped>
h1 { font-size: 1.6rem; }
.tuiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr)); margin-bottom: 20px; }
.tuile { padding: 16px; display: grid; gap: 4px; text-decoration: none; color: var(--texte); }
.tuile:hover { border-color: var(--primaire); }
.tuile.alerte { border-color: var(--danger); background: var(--danger-clair); margin: 0; }
.chiffre { font-size: 2rem; font-weight: 800; line-height: 1; color: var(--primaire); }
.tuile.alerte .chiffre { color: var(--danger); }
.mois { padding: 18px; }
.mois h2 { margin: 0 0 10px; font-size: 1.15rem; }
.mois h2::first-letter { text-transform: uppercase; }
.mois dl { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); margin: 0 0 10px; }
.mois dt { color: var(--texte-doux); font-size: 0.9rem; }
.mois dd { margin: 0; font-weight: 750; font-size: 1.15rem; }
</style>
