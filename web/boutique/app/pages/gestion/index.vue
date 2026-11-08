<script setup lang="ts">
import type { PageCommandes, Statut } from '~/types/commandes'
import { classeStatut } from '~/types/commandes'

useSeoMeta({ title: 'Commandes', robots: 'noindex' })
const ONGLETS: { cle: string; titre: string; statuts: Statut[] }[] = [
  { cle: 'a-traiter', titre: 'À traiter', statuts: ['en_attente', 'devis_demande'] },
  { cle: 'en-cours', titre: 'En cours', statuts: ['confirmee', 'en_preparation', 'prete', 'en_livraison'] },
  { cle: 'devis', titre: 'Devis envoyés', statuts: ['devis_envoye'] },
  { cle: 'terminees', titre: 'Terminées', statuts: ['livree', 'annulee', 'devis_refuse'] },
  { cle: 'toutes', titre: 'Toutes', statuts: [] },
]
const route = useRoute()
const router = useRouter()
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const onglet = computed(() => ONGLETS.find(o => o.cle === route.query.onglet) ?? ONGLETS[0]!)
const recherche = ref(typeof route.query.q === 'string' ? route.query.q : '')
const page = computed(() => Number(route.query.page) || 1)
const resultat = ref<PageCommandes | null>(null)
const erreur = ref('')

async function charger() {
  if (!autorise.value) return
  try {
    resultat.value = await appeler<PageCommandes>('/api/v1/admin/commandes', {
      query: { statut: onglet.value.statuts, q: recherche.value || undefined, page: page.value, par_page: 30 },
    })
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function chercher() {
  void router.replace({ query: { ...route.query, q: recherche.value || undefined, page: undefined } })
}

watch([verifie, () => route.query], charger, { deep: true })
</script>

<template>
  <section class="conteneur gestion">
    <AccesEquipe>
      <div class="entete-gestion">
        <h1>Commandes</h1>
        <form role="search" class="recherche" @submit.prevent="chercher">
          <label for="q" class="visuellement-cache">Référence, nom ou téléphone</label>
          <input id="q" v-model="recherche" type="search" placeholder="BB-1001, nom, téléphone">
          <button type="submit" class="bouton bouton-secondaire">Chercher</button>
        </form>
      </div>
      <nav class="onglets" aria-label="Filtrer par étape">
        <NuxtLink
          v-for="o in ONGLETS" :key="o.cle" :to="{ query: { ...route.query, onglet: o.cle, page: undefined } }"
          class="onglet" :class="{ actif: o.cle === onglet.cle }" :aria-current="o.cle === onglet.cle ? 'page' : undefined"
        >{{ o.titre }}</NuxtLink>
      </nav>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <p v-if="resultat && !resultat.elements.length" class="aide">Rien ici pour le moment.</p>
      <ul v-if="resultat" class="file">
        <li v-for="c in resultat.elements" :key="c.reference">
          <NuxtLink :to="`/gestion/commandes/${c.reference}`" class="carte ligne-file">
            <span class="ref">{{ c.reference }}</span>
            <span :class="classeStatut(c.statut)">{{ c.statut_libelle }}</span>
            <span class="client">{{ c.etablissement ?? c.nom_client }}<small>{{ formaterTelephone(c.telephone) }}</small></span>
            <span class="quand">{{ formaterDateHeure(c.cree_le) }}<small v-if="c.date_promise">Promise le {{ formaterDate(c.date_promise) }}</small></span>
            <span class="montant">{{ formaterFcfa(c.total) }}<small>{{ c.montant_paye >= c.total ? 'Payée' : c.mode_livraison === 'livraison' ? c.zone_nom : 'Retrait' }}</small></span>
          </NuxtLink>
        </li>
      </ul>
      <nav v-if="resultat && resultat.total > resultat.par_page" class="pages" aria-label="Pages">
        <NuxtLink v-if="page > 1" :to="{ query: { ...route.query, page: page - 1 } }" class="bouton bouton-secondaire">Précédentes</NuxtLink>
        <span class="aide">Page {{ page }} sur {{ Math.ceil(resultat.total / resultat.par_page) }}</span>
        <NuxtLink v-if="page * resultat.par_page < resultat.total" :to="{ query: { ...route.query, page: page + 1 } }" class="bouton bouton-secondaire">Suivantes</NuxtLink>
      </nav>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.gestion { padding-top: 24px; }
.entete-gestion { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.entete-gestion h1 { margin: 0; }
.recherche { display: flex; gap: 8px; flex: 1; max-width: 420px; }
.recherche input { flex: 1; min-width: 0; min-height: 44px; padding: 0 0.9em; border: 1.5px solid var(--bordure); border-radius: 999px; font: inherit; }
.onglets { display: flex; gap: 6px; overflow-x: auto; margin: 16px 0; padding-bottom: 4px; }
.onglet { padding: 8px 14px; border-radius: 999px; text-decoration: none; color: var(--texte); background: var(--fond-doux); white-space: nowrap; font-weight: 600; }
.onglet.actif { background: var(--primaire); color: #fff; }
.file { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ligne-file {
  display: grid; gap: 4px 16px; padding: 12px 16px; color: inherit; text-decoration: none; align-items: center;
  grid-template-columns: auto 1fr auto;
}
.ligne-file:hover { border-color: var(--primaire); }
.ligne-file small { display: block; color: var(--texte-doux); font-size: 0.85rem; font-weight: 400; }
.ref { font-weight: 800; }
.client { grid-column: 1 / -1; }
.quand { grid-column: 1 / 3; font-size: 0.92rem; }
.montant { font-weight: 700; text-align: right; }
@media (min-width: 820px) {
  .ligne-file { grid-template-columns: 90px 170px minmax(0, 1fr) 170px 140px; }
  .client, .quand { grid-column: auto; }
}
.pages { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; }
</style>
