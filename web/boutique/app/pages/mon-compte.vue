<script setup lang="ts">
const route = useRoute()
useSeoMeta({ title: 'Mon compte', robots: 'noindex' })
const { utilisateur, attendre, changerMotDePasse, deconnexion } = useSession()
const chargement = ref(true)
const formulaire = reactive({ actuel: '', nouveau: '', confirmation: '' })
const erreur = ref('')
const succes = ref(false)
const envoi = ref(false)

async function changer() {
  erreur.value = ''
  succes.value = false
  if (formulaire.nouveau !== formulaire.confirmation) {
    erreur.value = 'Les deux mots de passe ne sont pas identiques.'
    return
  }
  envoi.value = true
  try {
    await changerMotDePasse(formulaire.actuel, formulaire.nouveau)
    Object.assign(formulaire, { actuel: '', nouveau: '', confirmation: '' })
    succes.value = true
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function seDeconnecter() {
  await deconnexion()
  await navigateTo('/')
}

onMounted(async () => {
  await attendre()
  chargement.value = false
})
</script>

<template>
  <section class="conteneur formulaire">
    <p v-if="chargement" class="aide">Chargement…</p>
    <div v-else-if="!utilisateur" class="carte">
      <h1>Mon compte</h1>
      <p>Connectez-vous pour voir votre compte.</p>
      <NuxtLink :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
    </div>
    <template v-else>
      <div class="carte">
        <h1>Mon compte</h1>
        <p><strong>{{ utilisateur.nom }}</strong><br>{{ formaterTelephone(utilisateur.telephone) }}</p>
        <div class="liens">
          <NuxtLink to="/mes-commandes" class="bouton bouton-secondaire">Mes commandes</NuxtLink>
          <button type="button" class="bouton bouton-discret" @click="seDeconnecter">Se déconnecter</button>
        </div>
      </div>
      <form class="carte" @submit.prevent="changer">
        <h2>Changer mon mot de passe</h2>
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <p v-if="succes" class="alerte alerte-succes" role="status">Mot de passe changé. Vos autres appareils devront se reconnecter.</p>
        <div class="champ">
          <label for="actuel">Mot de passe actuel</label>
          <input id="actuel" v-model="formulaire.actuel" type="password" autocomplete="current-password" required>
        </div>
        <div class="champ">
          <label for="nouveau">Nouveau mot de passe</label>
          <input id="nouveau" v-model="formulaire.nouveau" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
          <span class="aide">8 caractères au moins (12 pour un compte de l'équipe).</span>
        </div>
        <div class="champ">
          <label for="confirmation">Confirmer le nouveau mot de passe</label>
          <input id="confirmation" v-model="formulaire.confirmation" type="password" autocomplete="new-password" minlength="8" maxlength="128" required>
        </div>
        <button type="submit" class="bouton" :disabled="envoi">Changer mon mot de passe</button>
      </form>
    </template>
  </section>
</template>

<style scoped>
.formulaire { max-width: 520px; padding-top: 32px; display: grid; gap: 16px; }
.formulaire .carte { padding: 24px; display: grid; gap: 4px; justify-items: start; }
.formulaire .carte .champ { width: 100%; }
.formulaire h2 { margin: 0 0 8px; font-size: 1.15rem; }
.liens { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
</style>
