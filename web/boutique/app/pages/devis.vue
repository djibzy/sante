<script setup lang="ts">
useSeoMeta({ title: 'Demander un devis', robots: 'noindex' })
const { lignes, livraison, demande } = usePanier()
const { utilisateur } = useSession()
const { chiffrage, zones, enCours } = useChiffrage()
const { envoyer, envoi, erreur } = useEnvoiCommande('/api/v1/devis')
const monte = ref(false)
const formulaire = reactive({ etablissement: '', nom: '', telephone: '', email: '', note: '' })

onMounted(() => {
  monte.value = true
  formulaire.nom ||= utilisateur.value?.nom ?? ''
  formulaire.telephone ||= utilisateur.value?.telephone ?? ''
})

function valider() {
  void envoyer({
    etablissement: formulaire.etablissement,
    client: { nom: formulaire.nom, telephone: formulaire.telephone },
    email: formulaire.email.trim() || null,
    livraison: { ...livraison.value },
    lignes: demande.value,
    note: formulaire.note,
  })
}
</script>

<template>
  <section class="conteneur devis">
    <NuxtLink to="/panier" class="retour">Retour au panier</NuxtLink>
    <h1>Demander un devis</h1>
    <p class="intro">
      Pour un centre de santé, une clinique, une école de santé ou une ONG : nous établissons un
      devis avec vos quantités, la broderie de votre logo et le prix professionnel, que vous
      pouvez télécharger en PDF et accepter en ligne.
    </p>
    <p v-if="!monte" class="aide">Chargement…</p>
    <div v-else-if="!lignes.length" class="carte vide">
      <p>Ajoutez d'abord au panier les articles et les quantités souhaités.</p>
      <NuxtLink to="/" class="bouton">Voir les produits</NuxtLink>
    </div>
    <form v-else class="colonnes" @submit.prevent="valider">
      <div class="carte bloc">
        <div class="champ">
          <label for="etablissement">Structure</label>
          <input id="etablissement" v-model="formulaire.etablissement" required minlength="2" maxlength="160" placeholder="CSCom, clinique, école, ONG…">
        </div>
        <div class="champ">
          <label for="nom">Personne à contacter</label>
          <input id="nom" v-model="formulaire.nom" autocomplete="name" required minlength="2" maxlength="120">
        </div>
        <div class="champ">
          <label for="telephone">Téléphone</label>
          <input id="telephone" v-model="formulaire.telephone" type="tel" inputmode="tel" autocomplete="tel" required>
        </div>
        <div class="champ">
          <label for="email">Courriel (facultatif)</label>
          <input id="email" v-model="formulaire.email" type="email" autocomplete="email" maxlength="200">
        </div>
        <ChoixLivraison :zones="zones" adresse-requise />
        <div class="champ">
          <label for="note">Votre besoin</label>
          <textarea id="note" v-model="formulaire.note" maxlength="1000" rows="4" placeholder="Logo à broder, répartition des tailles, date souhaitée…" />
          <span class="aide">N'indiquez aucune information médicale.</span>
        </div>
      </div>
      <aside class="carte bloc">
        <h2>Estimation au prix public</h2>
        <RecapitulatifPrix :chiffrage="chiffrage" :en-cours="enCours" />
        <p class="aide">Le devis final tient compte des quantités et du prix professionnel.</p>
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <button type="submit" class="bouton bouton-large" :disabled="envoi || !chiffrage?.commandable">
          {{ envoi ? 'Envoi…' : 'Envoyer la demande de devis' }}
        </button>
      </aside>
    </form>
  </section>
</template>

<style scoped>
.devis { padding-top: 20px; }
.retour { display: inline-block; margin-bottom: 12px; font-size: 0.95rem; }
.intro { max-width: 68ch; color: var(--texte-doux); }
.vide { padding: 24px; display: grid; justify-items: start; gap: 8px; }
.colonnes { display: grid; gap: 20px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 360px; align-items: start; } }
.bloc { padding: 20px; display: grid; gap: 4px; }
.bloc h2 { margin: 0 0 12px; font-size: 1.15rem; }
aside.bloc { gap: 12px; }
</style>
