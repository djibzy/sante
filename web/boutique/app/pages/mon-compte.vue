<script setup lang="ts">
const route = useRoute()
useSeoMeta({ title: 'Mon compte', robots: 'noindex' })
const { utilisateur, attendre, changerMotDePasse, deconnexion, mesDonnees, supprimerCompte, fermer } = useSession()
const { appeler } = useApiBoutique()
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

// Droits sur les données : tout télécharger, ou supprimer le compte.
const telechargement = ref(false)
const erreurDonnees = ref('')
async function telechargerMesDonnees() {
  telechargement.value = true
  erreurDonnees.value = ''
  try {
    const [compte, boutique] = await Promise.all([mesDonnees(), appeler<Record<string, unknown>>('/api/v1/mes-donnees')])
    const fichier = new Blob([JSON.stringify({ compte, boutique }, null, 2)], { type: 'application/json' })
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(fichier)
    lien.download = 'mes-donnees-yasal-sante.json'
    lien.click()
    setTimeout(() => URL.revokeObjectURL(lien.href), 60_000)
  } catch (e) {
    erreurDonnees.value = messageErreur(e)
  } finally {
    telechargement.value = false
  }
}

const suppression = reactive({ ouverte: false, motDePasse: '', confirme: false, envoi: false, erreur: '' })
async function supprimer() {
  suppression.erreur = ''
  suppression.envoi = true
  try {
    // La boutique vérifie d'abord qu'aucune commande n'est attendue (elle garde alors vos coordonnées).
    const { possible, en_cours: enCours } = await appeler<{ possible: boolean, en_cours: string[] }>('/api/v1/mes-donnees/oubli')
    if (!possible) {
      suppression.erreur = `Commande en cours : ${enCours.join(', ')}. Attendez sa remise, ou annulez-la, avant de supprimer votre compte.`
      return
    }
    await supprimerCompte(suppression.motDePasse)
    await appeler('/api/v1/mes-donnees/oubli', { method: 'POST' })
    fermer()
    await navigateTo({ path: '/', query: { compte: 'supprime' } })
  } catch (e) {
    suppression.erreur = messageErreur(e)
  } finally {
    suppression.envoi = false
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
      <section class="carte" aria-labelledby="titre-donnees">
        <h2 id="titre-donnees">Mes données</h2>
        <p class="aide">
          Votre compte, vos consentements, vos commandes passées avec ce compte et vos avis, dans
          un fichier. Les commandes passées sans compte se retrouvent avec leur lien de suivi.
        </p>
        <div v-if="erreurDonnees" class="alerte alerte-erreur" role="alert">{{ erreurDonnees }}</div>
        <button type="button" class="bouton bouton-secondaire" :disabled="telechargement" @click="telechargerMesDonnees">
          Télécharger mes données
        </button>
        <button v-if="!suppression.ouverte" type="button" class="bouton bouton-discret danger" @click="suppression.ouverte = true">
          Supprimer mon compte…
        </button>
        <form v-else class="suppression" @submit.prevent="supprimer">
          <p>
            Votre compte sera anonymisé et vos sessions fermées. Vos commandes terminées sont
            anonymisées ; les commandes facturées sont gardées 10 ans pour la comptabilité, sans
            lien avec vous. Vos avis sont effacés. C'est définitif.
          </p>
          <div v-if="suppression.erreur" class="alerte alerte-erreur" role="alert">{{ suppression.erreur }}</div>
          <div class="champ">
            <label for="mdp-suppression">Mot de passe</label>
            <input id="mdp-suppression" v-model="suppression.motDePasse" type="password" autocomplete="current-password" required>
          </div>
          <label class="case"><input v-model="suppression.confirme" type="checkbox" required> Je veux supprimer mon compte</label>
          <div class="liens">
            <button type="submit" class="bouton danger-plein" :disabled="suppression.envoi || !suppression.confirme">Supprimer définitivement</button>
            <button type="button" class="bouton bouton-discret" @click="suppression.ouverte = false">Annuler</button>
          </div>
        </form>
      </section>
    </template>
  </section>
</template>

<style scoped>
.formulaire { max-width: 520px; padding-top: 32px; display: grid; gap: 16px; }
.formulaire .carte { padding: 24px; display: grid; gap: 4px; justify-items: start; }
.formulaire .carte .champ { width: 100%; }
.formulaire h2 { margin: 0 0 8px; font-size: 1.15rem; }
.liens { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.danger { color: var(--danger); }
.danger-plein { background: var(--danger); }
.suppression { display: grid; gap: 8px; width: 100%; margin-top: 8px; padding-top: 12px; border-top: 1px solid var(--bordure); }
.suppression p { margin: 0; }
.case { display: flex; gap: 8px; align-items: center; font-weight: 600; }
</style>
