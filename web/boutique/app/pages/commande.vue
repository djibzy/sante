<script setup lang="ts">
useSeoMeta({ title: 'Commander', robots: 'noindex' })
const { lignes, livraison, demande } = usePanier()
const { utilisateur } = useSession()
const { chiffrage, zones, enCours } = useChiffrage()
const { envoyer, envoi, erreur } = useEnvoiCommande('/api/v1/commandes')
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
        <RecapitulatifPrix :chiffrage="chiffrage" :en-cours="enCours" />
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <button type="submit" class="bouton bouton-large" :disabled="envoi || !chiffrage?.commandable">
          {{ envoi ? 'Envoi…' : 'Confirmer la commande' }}
        </button>
      </aside>
    </form>
  </section>
</template>

<style scoped>
.commande { padding-top: 20px; }
.retour { display: inline-block; margin-bottom: 12px; font-size: 0.95rem; }
.vide { padding: 24px; display: grid; justify-items: start; gap: 8px; }
.colonnes { display: grid; gap: 20px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 360px; align-items: start; } }
.bloc { padding: 20px; display: grid; gap: 4px; }
.bloc h2 { margin: 0 0 12px; font-size: 1.15rem; }
aside.bloc { gap: 12px; }
aside p { margin: 0; }
</style>
