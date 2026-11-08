<script setup lang="ts">
import type { CommandeResume } from '~/types/commandes'
import { classeStatut } from '~/types/commandes'

useSeoMeta({ title: 'Mes commandes', robots: 'noindex' })
const route = useRoute()
const { utilisateur, attendre, deconnexion } = useSession()
const { appeler } = useApiBoutique()
const { suivis } = usePanier()
const commandes = ref<CommandeResume[]>([])
const chargement = ref(true)
const erreur = ref('')

// Demandes passées sans compte sur cet appareil, et pas déjà listées par le compte.
const autres = computed(() => suivis.value.filter(s => !commandes.value.some(c => c.reference === s.reference)))

async function charger() {
  chargement.value = true
  await attendre()
  try {
    commandes.value = utilisateur.value ? await appeler<CommandeResume[]>('/api/v1/mes-commandes') : []
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

async function seDeconnecter() {
  await deconnexion()
  commandes.value = []
}

onMounted(charger)
</script>

<template>
  <section class="conteneur mes-commandes">
    <h1>Mes commandes</h1>
    <p v-if="chargement" class="aide">Chargement…</p>
    <template v-else>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="utilisateur" class="compte">
        <span>Connecté : <strong>{{ utilisateur.nom }}</strong></span>
        <button type="button" class="bouton bouton-discret" @click="seDeconnecter">Se déconnecter</button>
      </div>
      <div v-else class="carte invitation">
        <p>Connectez-vous pour retrouver vos commandes sur tous vos appareils.</p>
        <NuxtLink :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
      </div>

      <ul v-if="commandes.length" class="liste">
        <li v-for="c in commandes" :key="c.reference">
          <NuxtLink :to="`/suivi/${c.reference}`" class="carte element">
            <span class="ref">{{ c.est_devis ? 'Devis' : 'Commande' }} {{ c.reference }}</span>
            <span :class="classeStatut(c.statut)">{{ c.statut_libelle }}</span>
            <span class="aide">{{ formaterDate(c.cree_le) }}, {{ c.nombre_articles }} article{{ c.nombre_articles > 1 ? 's' : '' }}</span>
            <strong>{{ formaterFcfa(c.total) }}</strong>
          </NuxtLink>
        </li>
      </ul>

      <template v-if="autres.length">
        <h2>Sur cet appareil</h2>
        <ul class="liste">
          <li v-for="s in autres" :key="s.reference">
            <NuxtLink :to="{ path: `/suivi/${s.reference}`, query: { cle: s.cle } }" class="carte element">
              <span class="ref">{{ s.est_devis ? 'Devis' : 'Commande' }} {{ s.reference }}</span>
              <span class="aide">{{ formaterDate(s.cree_le) }}</span>
            </NuxtLink>
          </li>
        </ul>
      </template>
      <p v-if="!commandes.length && !autres.length" class="aide">Aucune commande pour le moment.</p>
    </template>
  </section>
</template>

<style scoped>
.mes-commandes { padding-top: 24px; max-width: 760px; }
.compte { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.invitation { padding: 18px; margin-bottom: 20px; display: grid; justify-items: start; gap: 4px; }
.invitation p { margin: 0 0 8px; }
.liste { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.element { display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; padding: 14px 16px; color: inherit; text-decoration: none; }
.element:hover { border-color: var(--primaire); }
.ref { font-weight: 700; }
.element > :nth-child(2) { justify-self: end; }
.element strong { justify-self: end; }
</style>
