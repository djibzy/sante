<script setup lang="ts">
import type { TableauDeBord } from '~/types/tableau'

useSeoMeta({ title: 'Tableau de bord', robots: 'noindex' })
const PERIODES = [
  { cle: '7j', titre: '7 jours' },
  { cle: '30j', titre: '30 jours' },
  { cle: 'mois', titre: 'Ce mois' },
  { cle: 'mois-dernier', titre: 'Mois dernier' },
  { cle: '12m', titre: '12 mois' },
]
const MOYENS: Record<string, string> = {
  especes: 'Espèces', orange_money: 'Orange Money', moov_money: 'Moov Money', mobile_money: 'Paiement mobile',
  virement: 'Virement', cheque: 'Chèque',
}
const route = useRoute()
const router = useRouter()
const { appeler, telecharger } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const donnees = ref<TableauDeBord | null>(null)
const chargement = ref(false)
const erreur = ref('')
const libre = reactive({ du: '', au: '' })

const jour = (d: Date) => d.toISOString().slice(0, 10)
function bornes(): { du?: string, au?: string } {
  if (typeof route.query.du === 'string' && typeof route.query.au === 'string') return { du: route.query.du, au: route.query.au }
  const aujourdhui = new Date()
  const ilYa = (jours: number) => jour(new Date(aujourdhui.getTime() - jours * 86_400_000))
  const debutMois = new Date(Date.UTC(aujourdhui.getUTCFullYear(), aujourdhui.getUTCMonth(), 1))
  switch (route.query.periode) {
    case '7j': return { du: ilYa(6), au: jour(aujourdhui) }
    case 'mois': return { du: jour(debutMois), au: jour(aujourdhui) }
    case 'mois-dernier': return {
      du: jour(new Date(Date.UTC(debutMois.getUTCFullYear(), debutMois.getUTCMonth() - 1, 1))),
      au: jour(new Date(debutMois.getTime() - 86_400_000)),
    }
    case '12m': return { du: ilYa(364), au: jour(aujourdhui) }
    default: return {} // 30 derniers jours, calculés par le serveur
  }
}
// Exports CSV de la période affichée (factures, encaissements, commandes), pour Excel.
const EXPORTS = [
  { nature: 'factures', libelle: 'Factures' },
  { nature: 'encaissements', libelle: 'Encaissements' },
  { nature: 'commandes', libelle: 'Commandes' },
]
const exportEnCours = ref('')
async function exporter(nature: string) {
  if (!donnees.value) return
  exportEnCours.value = nature
  try {
    const { du, au } = donnees.value
    await telecharger(`/api/v1/admin/exports/${nature}.csv?du=${du}&au=${au}`, `bibou-${nature}-${du}-${au}.csv`)
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    exportEnCours.value = ''
  }
}

const periode = computed(() => (route.query.du ? 'libre' : (route.query.periode as string) || '30j'))

async function charger() {
  if (!autorise.value) return
  chargement.value = true
  try {
    donnees.value = await appeler<TableauDeBord>('/api/v1/admin/tableau-de-bord', { query: bornes() })
    erreur.value = ''
    libre.du = donnees.value.du
    libre.au = donnees.value.au
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

function afficherPeriode() {
  if (libre.du && libre.au) void router.replace({ query: { du: libre.du, au: libre.au } })
}

const pourcent = (x: number | null) => (x === null ? '–' : `${Math.round(x * 100)} %`)
const nombre = (x: number | null, unite: string) => (x === null ? '–' : `${x.toLocaleString('fr-FR')} ${unite}`)
const tuiles = computed(() => {
  const d = donnees.value
  if (!d) return []
  return [
    { titre: "Chiffre d'affaires remis", valeur: formaterFcfa(d.ventes.chiffre_affaires), detail: `${d.ventes.commandes_livrees} commande(s) remise(s)` },
    {
      titre: 'Encaissé',
      valeur: formaterFcfa(d.ventes.encaisse),
      detail: [
        d.ventes.encaisse_en_ligne ? `dont ${formaterFcfa(d.ventes.encaisse_en_ligne)} en ligne` : 'à la livraison et au retrait',
        d.ventes.rembourse ? `${formaterFcfa(d.ventes.rembourse)} rendus aux clients` : '',
      ].filter(Boolean).join(' · '),
    },
    { titre: 'Panier moyen', valeur: d.ventes.panier_moyen === null ? '–' : formaterFcfa(d.ventes.panier_moyen), detail: 'commandes remises' },
    { titre: 'Commandes reçues', valeur: String(d.ventes.commandes_recues), detail: `${d.ventes.annulees} annulée(s)` },
    { titre: 'Reste à encaisser', valeur: formaterFcfa(d.ventes.a_encaisser), detail: 'sur des commandes déjà remises' },
    { titre: 'Clients', valeur: String(d.clients.clients), detail: `dont ${d.clients.nouveaux} nouveau(x)` },
  ]
})
const alertes = computed(() => {
  const a = donnees.value?.alertes
  const relire = donnees.value?.clients.avis_a_relire ?? 0
  if (!a) return []
  return [
    { titre: 'À confirmer', nombre: a.a_traiter, lien: '/gestion?onglet=a-traiter' },
    { titre: 'Acomptes attendus', nombre: a.acomptes_attendus, lien: '/gestion?onglet=acomptes' },
    { titre: 'En retard', nombre: a.en_retard, lien: '/gestion?onglet=en-cours' },
    { titre: 'Stock bas', nombre: a.stock_bas, lien: '/gestion/stock' },
    { titre: 'Avis à relire', nombre: relire, lien: '/gestion/avis' },
    { titre: 'Paiements à vérifier', nombre: a.paiements_a_verifier, lien: '/gestion?onglet=en-cours' },
    { titre: 'À rembourser', nombre: a.a_rembourser, lien: '/gestion?onglet=a-rembourser' },
    { titre: 'SMS non partis', nombre: a.sms_en_echec, lien: null },
  ]
})
const points = computed(() => (donnees.value?.serie ?? []).map(p => ({
  debut: p.debut, valeur: p.chiffre_affaires, detail: `${p.commandes} commande${p.commandes > 1 ? 's' : ''}`,
})))

watch([verifie, () => route.query], charger, { deep: true })
</script>

<template>
  <section class="conteneur gestion">
    <AccesEquipe>
      <h1>Tableau de bord</h1>
      <div class="filtres">
        <nav class="onglets" aria-label="Période">
          <NuxtLink
            v-for="p in PERIODES" :key="p.cle" :to="{ query: { periode: p.cle } }" class="onglet"
            :class="{ actif: periode === p.cle }" :aria-current="periode === p.cle ? 'page' : undefined"
          >{{ p.titre }}</NuxtLink>
        </nav>
        <form class="libre" @submit.prevent="afficherPeriode">
          <label>Du <input v-model="libre.du" type="date" required></label>
          <label>au <input v-model="libre.au" type="date" required></label>
          <button type="submit" class="bouton bouton-secondaire">Afficher</button>
        </form>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="donnees" class="contenu" :class="{ attente: chargement }">
        <div class="periode-exports">
          <p class="aide">Du {{ formaterDate(donnees.du) }} au {{ formaterDate(donnees.au) }} inclus.</p>
          <div class="exports" role="group" aria-label="Exports pour la comptabilité (CSV)">
            <span class="aide">Exporter pour le comptable :</span>
            <button
              v-for="e in EXPORTS" :key="e.nature" type="button" class="bouton bouton-discret"
              :disabled="exportEnCours === e.nature" @click="exporter(e.nature)"
            >
              {{ exportEnCours === e.nature ? 'Préparation…' : e.libelle }}
            </button>
          </div>
        </div>

        <ul class="alertes" aria-label="À surveiller aujourd'hui">
          <li v-for="a in alertes" :key="a.titre" :class="{ calme: !a.nombre }">
            <NuxtLink v-if="a.lien" :to="a.lien"><strong>{{ a.nombre }}</strong> {{ a.titre }}</NuxtLink>
            <span v-else><strong>{{ a.nombre }}</strong> {{ a.titre }}</span>
          </li>
        </ul>

        <div class="tuiles">
          <div v-for="t in tuiles" :key="t.titre" class="carte tuile">
            <p class="titre">{{ t.titre }}</p>
            <p class="valeur">{{ t.valeur }}</p>
            <p class="detail">{{ t.detail }}</p>
          </div>
        </div>

        <div class="carte bloc">
          <GraphiqueBarres
            :titre="`Chiffre d'affaires remis, par ${donnees.pas === 'jour' ? 'jour' : 'semaine'}`"
            :points="points" :pas="donnees.pas"
          />
        </div>

        <div class="colonnes">
          <div class="carte bloc">
            <h2>Délais</h2>
            <dl class="mesures">
              <div><dt>Confirmation d'une commande</dt><dd>{{ nombre(donnees.delais.confirmation_heures, 'h') }}</dd></div>
              <div><dt>De la commande à la remise</dt><dd>{{ nombre(donnees.delais.livraison_jours, 'j') }}</dd></div>
              <div><dt>Remises à la date promise</dt><dd>{{ pourcent(donnees.delais.a_l_heure) }}</dd></div>
            </dl>
          </div>
          <div class="carte bloc">
            <h2>Devis</h2>
            <dl class="mesures">
              <div><dt>Demandés</dt><dd>{{ donnees.devis.demandes }}</dd></div>
              <div><dt>Envoyés</dt><dd>{{ donnees.devis.envoyes }}</dd></div>
              <div><dt>Acceptés / refusés</dt><dd>{{ donnees.devis.acceptes }} / {{ donnees.devis.refuses }}</dd></div>
              <div><dt>Taux d'acceptation</dt><dd>{{ pourcent(donnees.devis.taux_acceptation) }}</dd></div>
            </dl>
          </div>
          <div class="carte bloc">
            <h2>Avis clients</h2>
            <dl class="mesures">
              <div>
                <dt>Note moyenne</dt>
                <dd class="note">
                  <NoteEtoiles v-if="donnees.clients.note_moyenne" :note="donnees.clients.note_moyenne" :taille="14" />
                  {{ donnees.clients.note_moyenne === null ? '–' : `${donnees.clients.note_moyenne.toLocaleString('fr-FR')} / 5` }}
                </dd>
              </div>
              <div><dt>Publiés sur la période</dt><dd>{{ donnees.clients.avis_publies }}</dd></div>
              <div><dt>À relire</dt><dd>{{ donnees.clients.avis_a_relire }}</dd></div>
            </dl>
          </div>
        </div>

        <div class="colonnes">
          <div class="carte bloc">
            <h2>Meilleures ventes</h2>
            <p v-if="!donnees.meilleures_ventes.length" class="aide">Aucune commande remise sur la période.</p>
            <table v-else class="tableau">
              <thead><tr><th scope="col">Article</th><th scope="col">Quantité</th><th scope="col">Montant</th></tr></thead>
              <tbody>
                <tr v-for="v in donnees.meilleures_ventes" :key="v.libelle">
                  <td><NuxtLink v-if="v.produit_slug" :to="`/produits/${v.produit_slug}`">{{ v.libelle }}</NuxtLink><template v-else>{{ v.libelle }}</template></td>
                  <td>{{ v.quantite }}</td>
                  <td>{{ formaterFcfa(v.montant) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="carte bloc">
            <h2>Encaissé par moyen</h2>
            <p v-if="!Object.keys(donnees.ventes.encaisse_par_moyen).length" class="aide">Aucun encaissement sur la période.</p>
            <table v-else class="tableau">
              <tbody>
                <tr v-for="(montant, moyen) in donnees.ventes.encaisse_par_moyen" :key="moyen">
                  <th scope="row">{{ MOYENS[moyen] ?? moyen }}</th><td>{{ formaterFcfa(montant) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <p v-else-if="!erreur" class="aide">Chargement…</p>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.gestion { padding-top: 20px; }
.filtres { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; margin: 12px 0 16px; }
.onglets { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; }
.onglet { padding: 8px 14px; border-radius: 999px; text-decoration: none; color: var(--texte); background: var(--fond-doux); white-space: nowrap; font-weight: 600; }
.onglet.actif { background: var(--primaire); color: #fff; }
.libre { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.libre label { display: flex; align-items: center; gap: 6px; font-weight: 600; }
.libre input { min-height: 40px; padding: 0 8px; border: 1.5px solid var(--bordure); border-radius: 8px; }
.contenu { display: grid; gap: 16px; transition: opacity 0.2s; }
.contenu.attente { opacity: 0.55; }
.contenu > .aide { margin: 0; }
.periode-exports { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 6px 16px; }
.periode-exports p { margin: 0; }
.exports { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.alertes { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
.alertes li a, .alertes li span { display: inline-flex; gap: 6px; align-items: baseline; padding: 8px 12px; border-radius: 10px; background: var(--accent-clair); color: var(--accent-texte); text-decoration: none; font-weight: 600; }
.alertes li.calme a, .alertes li.calme span { background: var(--fond-doux); color: var(--texte-doux); }
.tuiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); }
.tuile { padding: 14px 16px; display: grid; gap: 2px; }
.tuile p { margin: 0; }
.tuile .titre { color: var(--texte-doux); font-size: 0.9rem; font-weight: 600; }
.tuile .valeur { font-size: 1.5rem; font-weight: 800; }
.tuile .detail { color: var(--texte-doux); font-size: 0.85rem; }
.bloc { padding: 18px; display: grid; gap: 10px; align-content: start; }
.bloc h2 { margin: 0; font-size: 1.1rem; }
.colonnes { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); }
.mesures { margin: 0; display: grid; gap: 8px; }
.mesures div { display: flex; justify-content: space-between; gap: 12px; }
.mesures dt { color: var(--texte-doux); }
.mesures dd { margin: 0; font-weight: 700; white-space: nowrap; }
.mesures .note { display: inline-flex; align-items: center; gap: 6px; }
.tableau { border-collapse: collapse; width: 100%; font-size: 0.95rem; }
.tableau th, .tableau td { padding: 6px 8px 6px 0; text-align: left; border-bottom: 1px solid var(--bordure); }
.tableau td:last-child { text-align: right; white-space: nowrap; }
</style>
