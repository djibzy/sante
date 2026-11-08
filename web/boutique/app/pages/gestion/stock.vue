<script setup lang="ts">
import type { LigneStock } from '~/types/atelier'

useSeoMeta({ title: 'Stock', robots: 'noindex' })
type Operation = 'reception' | 'perte' | 'retour' | 'inventaire'
const OPERATIONS: Record<Operation, string> = {
  reception: 'Arrivage', perte: 'Perte ou casse', retour: 'Retour client', inventaire: 'Comptage',
}
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const lignes = ref<LigneStock[]>([])
const alertesSeulement = ref(false)
const erreur = ref('')
const message = ref('')
const choisie = ref<LigneStock | null>(null)
const operation = reactive({ type: 'reception' as Operation, quantite: 1, note: '' })

const affichees = computed(() => alertesSeulement.value ? lignes.value.filter(l => l.alerte) : lignes.value)
const nombreAlertes = computed(() => lignes.value.filter(l => l.alerte).length)

async function charger() {
  if (!autorise.value) return
  try {
    lignes.value = await appeler<LigneStock[]>('/api/v1/admin/stock')
    if (choisie.value) choisie.value = lignes.value.find(l => cle(l) === cle(choisie.value!)) ?? null
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

const cle = (l: LigneStock) => `${l.produit_id}-${l.variante_id ?? ''}`

function choisir(ligne: LigneStock) {
  choisie.value = ligne
  operation.type = 'reception'
  operation.quantite = 1
  operation.note = ''
  message.value = ''
}

async function enregistrer() {
  const l = choisie.value
  if (!l) return
  erreur.value = ''
  const commun = { produit_id: l.produit_id, variante_id: l.variante_id, note: operation.note }
  try {
    if (operation.type === 'inventaire') {
      await appeler('/api/v1/admin/stock/inventaire', { method: 'POST', body: { ...commun, quantite_comptee: operation.quantite } })
    } else {
      await appeler('/api/v1/admin/stock/mouvements', { method: 'POST', body: { ...commun, quantite: operation.quantite, motif: operation.type } })
    }
    message.value = `${OPERATIONS[operation.type]} enregistré pour ${l.libelle}.`
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

watch(verifie, charger)
</script>

<template>
  <section class="conteneur stock">
    <AccesEquipe>
      <div class="entete-stock">
        <h1>Stock</h1>
        <label class="filtre"><input v-model="alertesSeulement" type="checkbox"> À commander seulement ({{ nombreAlertes }})</label>
      </div>
      <p class="aide">
        Articles vendus tels quels. Réservé : dans des commandes confirmées, pas encore préparées.
        Les articles fabriqués à l'atelier n'apparaissent pas ici.
      </p>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>

      <div class="colonnes">
        <table class="carte tableau">
          <thead>
            <tr><th scope="col">Article</th><th scope="col">En stock</th><th scope="col">Réservé</th><th scope="col">Disponible</th></tr>
          </thead>
          <tbody>
            <tr v-for="l in affichees" :key="cle(l)" :class="{ alerte: l.alerte, choisie: choisie && cle(choisie) === cle(l) }" tabindex="0" @click="choisir(l)" @keydown.enter="choisir(l)">
              <th scope="row">{{ l.libelle }}<small v-if="l.sku">{{ l.sku }}</small></th>
              <td>{{ l.niveau }}</td>
              <td>{{ l.reserve || '' }}</td>
              <td><strong>{{ l.disponible }}</strong><small v-if="l.alerte">Seuil {{ l.seuil_alerte }}</small></td>
            </tr>
          </tbody>
        </table>

        <aside class="carte panneau">
          <template v-if="choisie">
            <h2>{{ choisie.libelle }}</h2>
            <p class="aide">En stock : {{ choisie.niveau }}, disponible : {{ choisie.disponible }}</p>
            <form @submit.prevent="enregistrer">
              <fieldset class="types">
                <legend class="visuellement-cache">Opération</legend>
                <label v-for="(nom, type) in OPERATIONS" :key="type" :class="{ actif: operation.type === type }">
                  <input v-model="operation.type" type="radio" :value="type" class="visuellement-cache">{{ nom }}
                </label>
              </fieldset>
              <div class="champ">
                <label for="quantite-stock">{{ operation.type === 'inventaire' ? 'Quantité comptée' : 'Quantité' }}</label>
                <input id="quantite-stock" v-model.number="operation.quantite" type="number" :min="operation.type === 'inventaire' ? 0 : 1" inputmode="numeric" required>
              </div>
              <div class="champ">
                <label for="note-stock">Note (facultatif)</label>
                <input id="note-stock" v-model="operation.note" maxlength="300" placeholder="Fournisseur, bon de livraison…">
              </div>
              <button type="submit" class="bouton bouton-large">Enregistrer</button>
            </form>
          </template>
          <p v-else class="aide">Choisissez un article pour enregistrer un arrivage, une perte, un retour ou un comptage.</p>
        </aside>
      </div>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.stock { padding-top: 20px; }
.entete-stock { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.entete-stock h1 { margin: 0; }
.filtre { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.filtre input { width: 20px; height: 20px; accent-color: var(--primaire); }
.colonnes { display: grid; gap: 16px; margin-top: 12px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 340px; align-items: start; } }
.tableau { width: 100%; border-collapse: collapse; overflow: hidden; }
.tableau th, .tableau td { padding: 10px 12px; text-align: right; border-bottom: 1px solid var(--bordure); }
.tableau thead th { font-size: 0.85rem; color: var(--texte-doux); font-weight: 600; }
.tableau th[scope='row'], .tableau thead th:first-child { text-align: left; font-weight: 600; }
.tableau small { display: block; color: var(--texte-doux); font-weight: 400; font-size: 0.8rem; }
.tableau tbody tr { cursor: pointer; }
.tableau tbody tr:hover, .tableau tr.choisie { background: var(--primaire-clair); }
.tableau tr.alerte td:last-child strong { color: var(--danger); }
.panneau { padding: 18px; position: sticky; top: 84px; display: grid; gap: 8px; }
.panneau h2 { margin: 0; font-size: 1.1rem; }
.types { border: 0; padding: 0; margin: 0 0 12px; display: flex; flex-wrap: wrap; gap: 6px; }
.types label { padding: 8px 12px; border: 1.5px solid var(--bordure); border-radius: 999px; cursor: pointer; font-size: 0.92rem; }
.types label.actif { border-color: var(--primaire); background: var(--primaire-clair); font-weight: 650; }
</style>
