<script setup lang="ts">
useSeoMeta({ title: 'Créer un compte' })
const { inscription } = useSession()
const formulaire = reactive({
  nom: '',
  telephone: '',
  mot_de_passe: '',
  langue: 'fr',
  accepte_conditions: false,
})
const erreur = ref('')
const envoi = ref(false)

async function valider() {
  erreur.value = ''
  envoi.value = true
  try {
    await inscription({ ...formulaire })
    await navigateTo('/')
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
      <h1>Créer un compte</h1>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <form @submit.prevent="valider">
        <div class="champ">
          <label for="nom">Prénom et nom</label>
          <input id="nom" v-model="formulaire.nom" autocomplete="name" required minlength="2">
        </div>
        <div class="champ">
          <label for="telephone">Numéro de téléphone</label>
          <input id="telephone" v-model="formulaire.telephone" type="tel" inputmode="tel" autocomplete="tel" placeholder="76 12 34 56" required>
          <span class="aide">Il sert à vous connecter. Pour un numéro hors du Mali, ajoutez l'indicatif (+226…).</span>
        </div>
        <div class="champ">
          <label for="mot-de-passe">Mot de passe</label>
          <input id="mot-de-passe" v-model="formulaire.mot_de_passe" type="password" autocomplete="new-password" required minlength="8">
          <span class="aide">8 caractères au moins.</span>
        </div>
        <div class="champ">
          <label for="langue">Langue</label>
          <select id="langue" v-model="formulaire.langue">
            <option value="fr">Français</option>
            <option value="bm">Bambara</option>
          </select>
        </div>
        <label class="accord">
          <input v-model="formulaire.accepte_conditions" type="checkbox" required>
          J'accepte les conditions d'utilisation et la façon dont mes données sont traitées.
        </label>
        <button type="submit" class="bouton bouton-large" :disabled="envoi">Créer mon compte</button>
      </form>
      <p class="bas">Déjà un compte ? <NuxtLink to="/connexion">Se connecter</NuxtLink></p>
    </div>
  </section>
</template>

<style scoped>
.formulaire { max-width: 460px; padding-top: 32px; }
.formulaire .carte { padding: 24px; }
.accord { display: flex; gap: 10px; align-items: flex-start; margin: 4px 0 18px; font-size: 0.95rem; }
.accord input { margin-top: 4px; width: 18px; height: 18px; }
.bas { margin: 16px 0 0; text-align: center; }
</style>
