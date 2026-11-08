<script setup lang="ts">
const route = useRoute()
useSeoMeta({ title: 'Se connecter' })
const { connexion } = useSession()
const telephone = ref('')
const motDePasse = ref('')
const erreur = ref('')
const envoi = ref(false)

async function valider() {
  erreur.value = ''
  envoi.value = true
  try {
    await connexion(telephone.value, motDePasse.value)
    await navigateTo(cheminDeRetour(route.query.retour))
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}
</script>

<template>
  <section class="conteneur formulaire">
    <div class="carte">
      <h1>Se connecter</h1>
      <p class="aide">Un seul compte pour la boutique, la formation et les campagnes.</p>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <form @submit.prevent="valider">
        <div class="champ">
          <label for="telephone">Numéro de téléphone</label>
          <input id="telephone" v-model="telephone" type="tel" inputmode="tel" autocomplete="tel" placeholder="76 12 34 56" required>
        </div>
        <div class="champ">
          <label for="mot-de-passe">Mot de passe</label>
          <input id="mot-de-passe" v-model="motDePasse" type="password" autocomplete="current-password" required>
        </div>
        <button type="submit" class="bouton bouton-large" :disabled="envoi">Se connecter</button>
      </form>
      <p class="bas">Pas encore de compte ? <NuxtLink :to="{ path: '/inscription', query: route.query }">Créer un compte</NuxtLink></p>
    </div>
  </section>
</template>

<style scoped>
.formulaire { max-width: 460px; padding-top: 32px; }
.formulaire .carte { padding: 24px; }
.bas { margin: 16px 0 0; text-align: center; }
</style>
