<script setup lang="ts">
// Mot de passe oublié : un code par SMS, puis le nouveau mot de passe (connexion d'office).
const route = useRoute()
useSeoMeta({ title: 'Mot de passe oublié', robots: 'noindex' })
const { demanderCode, reinitialiser } = useSession()
const etape = ref<'numero' | 'code'>('numero')
const telephone = ref('')
const code = ref('')
const motDePasse = ref('')
const confirmation = ref('')
const message = ref('')
const erreur = ref('')
const envoi = ref(false)

async function envoyerCode() {
  erreur.value = ''
  envoi.value = true
  try {
    message.value = await demanderCode(telephone.value)
    etape.value = 'code'
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function valider() {
  erreur.value = ''
  if (motDePasse.value !== confirmation.value) {
    erreur.value = 'Les deux mots de passe ne sont pas identiques.'
    return
  }
  envoi.value = true
  try {
    await reinitialiser(telephone.value, code.value.trim(), motDePasse.value)
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
      <h1>Mot de passe oublié</h1>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <form v-if="etape === 'numero'" @submit.prevent="envoyerCode">
        <p class="aide">Nous envoyons un code par SMS au numéro de votre compte.</p>
        <div class="champ">
          <label for="telephone">Numéro de téléphone</label>
          <input id="telephone" v-model="telephone" type="tel" inputmode="tel" autocomplete="tel" placeholder="76 12 34 56" required>
        </div>
        <button type="submit" class="bouton bouton-large" :disabled="envoi">Recevoir un code par SMS</button>
      </form>
      <form v-else @submit.prevent="valider">
        <p class="alerte alerte-info" role="status">{{ message }}</p>
        <div class="champ">
          <label for="code">Code reçu par SMS</label>
          <input
            id="code" v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}"
            maxlength="6" placeholder="6 chiffres" required
          >
        </div>
        <div class="champ">
          <label for="nouveau">Nouveau mot de passe</label>
          <input id="nouveau" v-model="motDePasse" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
          <span class="aide">8 caractères au moins (12 pour un compte de l'équipe).</span>
        </div>
        <div class="champ">
          <label for="confirmation">Confirmer le mot de passe</label>
          <input id="confirmation" v-model="confirmation" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
        </div>
        <button type="submit" class="bouton bouton-large" :disabled="envoi">Changer mon mot de passe</button>
        <button type="button" class="bouton bouton-discret" :disabled="envoi" @click="envoyerCode">Renvoyer un code</button>
      </form>
      <p class="bas"><NuxtLink :to="{ path: '/connexion', query: route.query }">Retour à la connexion</NuxtLink></p>
    </div>
  </section>
</template>

<style scoped>
.formulaire { max-width: 460px; padding-top: 32px; }
.formulaire .carte { padding: 24px; }
form { display: grid; gap: 4px; }
form .bouton-discret { justify-self: center; margin-top: 8px; }
.bas { margin: 16px 0 0; text-align: center; }
</style>
