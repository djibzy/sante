<script setup lang="ts">
import type { Contrat } from '~/types/prestations'

useSeoMeta({ title: 'Contrats', robots: 'noindex' })
const { appeler } = useApiPrestations()
const { verifie, estGestionnaire } = useEquipe()
const contrats = ref<Contrat[] | null>(null)
const erreur = ref('')
const STATUTS = { actif: 'Actif', suspendu: 'Suspendu', termine: 'Terminé' }

async function charger() {
  if (!estGestionnaire.value) return
  try {
    contrats.value = await appeler<Contrat[]>('/api/v1/admin/contrats')
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}
watch(verifie, charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe gestion>
      <div class="entete-page">
        <h1>Contrats</h1>
        <NuxtLink to="/equipe/contrats/nouveau" class="bouton">Nouveau contrat</NuxtLink>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <p v-if="contrats && !contrats.length" class="aide">Aucun contrat pour l'instant : signez une demande ou créez un contrat.</p>
      <div v-if="contrats?.length" class="tableau-defilant" tabindex="0" role="region" aria-label="Liste des contrats">
        <table class="tableau">
          <thead>
            <tr><th scope="col">Contrat</th><th scope="col">Structure</th><th scope="col">Collectes</th><th scope="col">Formule</th><th scope="col">Partenaire</th><th scope="col">Statut</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in contrats" :key="c.id">
              <td><NuxtLink :to="`/equipe/contrats/${c.reference}`">{{ c.reference }}</NuxtLink></td>
              <td>{{ c.structure }}</td>
              <td>{{ c.libelle_jours }}</td>
              <td>{{ c.formule === 'forfait' ? `Forfait ${formaterFcfa(c.forfait_mensuel ?? 0)}` : 'À la pièce' }}</td>
              <td>{{ c.partenaire?.nom ?? '—' }}</td>
              <td><span class="pastille" :class="{ 'pastille-attente': c.statut !== 'actif' }">{{ STATUTS[c.statut] }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </AccesEquipe>
  </section>
</template>
