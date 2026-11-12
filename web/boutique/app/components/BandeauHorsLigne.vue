<script setup lang="ts">
const { enLigne } = useHorsLigne()
const { enAttente, issue } = useEnvoiDiffere()
const route = useRoute()
// Sur la page de commande, l'état de l'envoi s'affiche dans le formulaire.
const surLeFormulaire = computed(() => ['/commande', '/devis'].includes(route.path))
</script>

<template>
  <div v-if="!enLigne" class="bandeau" role="status">
    <div class="conteneur contenu">
      <strong>Hors ligne.</strong>
      <span>Vous consultez les pages enregistrées sur ce téléphone ; votre panier est gardé.</span>
      <NuxtLink to="/hors-ligne">Catalogue enregistré</NuxtLink>
    </div>
  </div>
  <div v-if="enAttente && !surLeFormulaire" class="bandeau" role="status">
    <div class="conteneur contenu">
      <strong>{{ enAttente.chemin === '/api/v1/devis' ? 'Demande de devis gardée.' : 'Commande gardée.' }}</strong>
      <span>Elle partira toute seule dès le retour du réseau.</span>
    </div>
  </div>
  <div v-if="issue && !surLeFormulaire" class="bandeau" :class="issue.nature" role="status">
    <div class="conteneur contenu">
      <template v-if="issue.nature === 'envoyee'">
        <strong>{{ issue.est_devis ? 'Demande de devis' : 'Commande' }} {{ issue.reference }} envoyée.</strong>
        <NuxtLink :to="{ path: `/suivi/${issue.reference}`, query: { cle: issue.cle } }" @click="issue = null">Voir le suivi</NuxtLink>
      </template>
      <template v-else>
        <strong>Votre commande gardée n'a pas pu partir :</strong>
        <span>{{ issue.message }}</span>
        <NuxtLink to="/panier" @click="issue = null">Ouvrir le panier</NuxtLink>
      </template>
      <button type="button" class="fermer" aria-label="Fermer" @click="issue = null">×</button>
    </div>
  </div>
</template>

<style scoped>
.bandeau { background: var(--accent-clair); color: var(--accent-texte); border-bottom: 1px solid var(--bordure); }
.bandeau.envoyee { background: var(--succes-clair); color: var(--succes); }
.bandeau.refusee { background: var(--danger-clair); color: var(--danger); }
.contenu { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; padding-top: 8px; padding-bottom: 8px; font-size: 0.92rem; }
.contenu a { color: inherit; font-weight: 700; }
.bandeau.envoyee, .bandeau.refusee { position: relative; }
.bandeau.envoyee .contenu, .bandeau.refusee .contenu { padding-right: 56px; }
.fermer {
  position: absolute; top: 50%; right: 8px; transform: translateY(-50%); border: 0; background: none;
  color: inherit; font-size: 1.4rem; line-height: 1; cursor: pointer; min-width: 44px; min-height: 44px;
}
</style>
