<script setup lang="ts">
useSeoMeta({ title: 'Commander', robots: 'noindex' })
const { lignes, livraison, demande } = usePanier()
const { utilisateur } = useSession()
const { chiffrage, zones, enCours } = useChiffrage()
const { envoyer, envoi, erreur, gardee, annulerEnvoiGarde } = useEnvoiCommande('/api/v1/commandes')
const { enLigne } = useHorsLigne()

// Sans réseau, le serveur ne peut pas chiffrer : total indicatif à partir des prix vus.
const estimation = computed(() => {
  if (enLigne.value) return null
  const montants = lignes.value.map(l => (l.prix_indicatif === null ? null : l.prix_indicatif * l.quantite))
  if (montants.some(m => m === null)) return null
  const articles = montants.reduce<number>((total, m) => total + (m ?? 0), 0)
  const zone = zones.value.find(z => z.id === livraison.value.zone_id)
  const frais = livraison.value.mode === 'retrait' ? 0 : zone?.frais ?? null
  return { articles, frais, total: frais === null ? null : articles + frais }
})
const peutEnvoyer = computed(() => (enLigne.value ? !!chiffrage.value?.commandable : lignes.value.length > 0))
const monte = ref(false)
const client = reactive({ nom: '', telephone: '' })
const note = ref('')

onMounted(() => {
  monte.value = true
  client.nom ||= utilisateur.value?.nom ?? ''
  client.telephone ||= utilisateur.value?.telephone ?? ''
})

function valider() {
  void envoyer({
    client: { ...client },
    livraison: { ...livraison.value },
    lignes: demande.value,
    note: note.value,
  })
}
</script>

<template>
  <section class="conteneur commande">
    <NuxtLink to="/panier" class="retour">Retour au panier</NuxtLink>
    <h1>Commander</h1>
    <p v-if="!monte" class="aide">Chargement…</p>
    <div v-else-if="!lignes.length" class="carte vide">
      <p>Votre panier est vide.</p>
      <NuxtLink to="/" class="bouton">Voir les produits</NuxtLink>
    </div>
    <form v-else class="colonnes" @submit.prevent="valider">
      <div class="carte bloc">
        <h2>Vos coordonnées</h2>
        <div class="champ">
          <label for="nom">Prénom et nom</label>
          <input id="nom" v-model="client.nom" autocomplete="name" required minlength="2" maxlength="120">
        </div>
        <div class="champ">
          <label for="telephone">Téléphone</label>
          <input id="telephone" v-model="client.telephone" type="tel" inputmode="tel" autocomplete="tel" placeholder="76 12 34 56" required>
          <span class="aide">Nous vous appelons à ce numéro pour confirmer la commande.</span>
        </div>
        <ChoixLivraison :zones="zones" adresse-requise />
        <div class="champ">
          <label for="note">Précisions (facultatif)</label>
          <textarea id="note" v-model="note" maxlength="500" rows="3" placeholder="Horaires où vous joindre, couleur souhaitée…" />
          <span class="aide">N'indiquez aucune information médicale.</span>
        </div>
      </div>

      <aside class="carte bloc">
        <h2>Paiement</h2>
        <p>
          À la livraison ou au retrait, en espèces ou par transfert Orange Money ou Moov Money.
          Rien à payer maintenant.
        </p>
        <RecapitulatifPrix v-if="enLigne" :chiffrage="chiffrage" :en-cours="enCours" />
        <dl v-else-if="estimation" class="estimation">
          <div><dt>Articles (prix indicatifs)</dt><dd>{{ formaterFcfa(estimation.articles) }}</dd></div>
          <div v-if="estimation.frais !== null">
            <dt>Livraison</dt><dd>{{ estimation.frais ? formaterFcfa(estimation.frais) : 'Gratuit' }}</dd>
          </div>
          <div v-if="estimation.total !== null" class="total"><dt>Total indicatif</dt><dd>{{ formaterFcfa(estimation.total) }}</dd></div>
          <p class="aide">Hors ligne : le total exact et la date vous sont confirmés par SMS à l'envoi.</p>
        </dl>
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <div v-if="gardee" class="alerte alerte-info" role="status">
          <p>
            Commande gardée sur ce téléphone : elle partira toute seule dès le retour du réseau,
            et vous recevrez un SMS de confirmation.
          </p>
          <button type="button" class="bouton bouton-discret" @click="annulerEnvoiGarde">Annuler l'envoi</button>
        </div>
        <button v-else type="submit" class="bouton bouton-large" :disabled="envoi || !peutEnvoyer">
          {{ envoi ? 'Envoi…' : enLigne ? 'Confirmer la commande' : 'Commander dès le retour du réseau' }}
        </button>
      </aside>
    </form>
  </section>
</template>

<style scoped>
.commande { padding-top: 20px; }
.estimation { margin: 0; display: grid; gap: 6px; }
.estimation div { display: flex; justify-content: space-between; gap: 12px; }
.estimation dt { color: var(--texte-doux); }
.estimation dd { margin: 0; font-weight: 650; white-space: nowrap; }
.estimation .total { padding-top: 8px; border-top: 1px solid var(--bordure); }
.estimation .total dd { font-size: 1.15rem; font-weight: 800; }
.estimation .aide { margin: 4px 0 0; }
.retour { display: inline-block; margin-bottom: 12px; font-size: 0.95rem; }
.vide { padding: 24px; display: grid; justify-items: start; gap: 8px; }
.colonnes { display: grid; gap: 20px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 360px; align-items: start; } }
.bloc { padding: 20px; display: grid; gap: 4px; }
.bloc h2 { margin: 0 0 12px; font-size: 1.15rem; }
aside.bloc { gap: 12px; }
aside p { margin: 0; }
</style>
