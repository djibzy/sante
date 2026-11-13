<script setup lang="ts">
import type { CommandeAPayer } from '~/types/paiements'

// Page du lien envoyé à un proche : le montant dû, les articles, et le paiement en ligne. Ni
// numéro, ni adresse, ni historique : ce lien ne sert qu'à payer.
const route = useRoute()
const reference = String(route.params.reference).toUpperCase()
const cle = ref(typeof route.query.cle === 'string' ? route.query.cle : '')
const retourPaiement = route.query.paiement === 'retour'
useSeoMeta({ title: `Payer la commande ${reference}`, robots: 'noindex' })

const { appeler } = useApiBoutique()
const commande = ref<CommandeAPayer | null>(null)
const erreur = ref('')
const chargement = ref(true)
const base = `/api/v1/payer/${reference}`
const requete = computed(() => ({ cle: cle.value }))

async function charger() {
  try {
    commande.value = await appeler<CommandeAPayer>(base, { query: requete.value })
    erreur.value = ''
  } catch (e) {
    const statut = (e as { status?: number }).status
    erreur.value = statut === 404
      ? retourPaiement && !cle.value
        ? 'Votre paiement est en cours de vérification : la personne pour qui vous payez reçoit un SMS dès qu\'il est confirmé.'
        : 'Ce lien de paiement n\'est plus valable. Demandez-en un nouveau à la personne qui vous l\'a envoyé.'
      : messageErreur(e)
  } finally {
    chargement.value = false
  }
}

onMounted(() => {
  if (!cle.value) {
    try { cle.value = sessionStorage.getItem(`bibou:payer:${reference}`) ?? '' } catch { /* navigation privée */ }
  }
  void charger()
})
</script>

<template>
  <section class="conteneur payer">
    <h1>Payer la commande <span class="ref">{{ reference }}</span></h1>
    <p v-if="chargement" class="aide">Chargement…</p>
    <p v-else-if="erreur" class="alerte alerte-info" role="status">{{ erreur }}</p>
    <div v-else-if="commande" class="colonnes">
      <div class="carte bloc">
        <p class="pour">Commande de <strong>{{ commande.pour }}</strong> · {{ commande.statut_libelle }}</p>
        <ul class="articles">
          <li v-for="(a, i) in commande.articles" :key="i"><span>{{ a.libelle }}</span><span class="quantite">× {{ a.quantite }}</span></li>
        </ul>
        <dl class="montants">
          <div><dt>Total</dt><dd>{{ formaterFcfa(commande.total) }}</dd></div>
          <div v-if="commande.montant_paye"><dt>Déjà payé</dt><dd>{{ formaterFcfa(commande.montant_paye) }}</dd></div>
          <div class="reste"><dt>Reste à payer</dt><dd>{{ formaterFcfa(commande.reste_a_payer) }}</dd></div>
        </dl>
        <p v-if="commande.acompte_restant" class="aide">
          La fabrication commence dès l'acompte de {{ formaterFcfa(commande.acompte_restant) }} reçu : vous pouvez ne
          payer que lui, le reste se règle à la livraison.
        </p>
      </div>
      <aside class="bloc-paiement">
        <PaiementMobile
          :commande="{ reference: commande.reference, montant_paye: commande.montant_paye }"
          :base="base" :requete="requete" :cle="cle" espace="payer" :partageable="false" @paye="charger"
        />
        <p class="aide">{{ commande.pour }} reçoit un reçu par SMS. Bibou ne voit jamais votre code secret.</p>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.payer { padding-top: 20px; }
.payer h1 { margin: 0 0 16px; }
.ref { white-space: nowrap; }
.colonnes { display: grid; gap: 16px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 380px; align-items: start; } }
.bloc { padding: 18px; display: grid; gap: 12px; }
.pour { margin: 0; }
.articles { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.articles li { display: flex; justify-content: space-between; gap: 12px; }
.quantite { color: var(--texte-doux); white-space: nowrap; }
.montants { margin: 0; display: grid; gap: 6px; padding-top: 10px; border-top: 1px solid var(--bordure); }
.montants div { display: flex; justify-content: space-between; gap: 12px; }
.montants dt { color: var(--texte-doux); }
.montants dd { margin: 0; font-weight: 650; white-space: nowrap; }
.montants .reste dd { font-size: 1.2rem; font-weight: 800; color: var(--primaire); }
.bloc-paiement { display: grid; gap: 10px; align-content: start; }
.bloc-paiement > .aide { margin: 0; }
.aide { margin: 0; }
</style>
