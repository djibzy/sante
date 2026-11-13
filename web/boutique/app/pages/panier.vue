<script setup lang="ts">
useSeoMeta({ title: 'Panier', robots: 'noindex' })
const { lignes, changerQuantite, reprise } = usePanier()
onBeforeUnmount(() => { reprise.value = null }) // le message ne vaut que pour cette visite
const { chiffrage, zones, enCours, erreur } = useChiffrage()
const monte = ref(false)
onMounted(() => { monte.value = true })

// Les remarques du serveur (article retiré, taille à choisir…) suivent l'ordre des lignes.
const remarque = (index: number) => chiffrage.value?.lignes[index]?.motif ?? null
const montant = (index: number) => chiffrage.value?.lignes[index]?.montant
const aLaDemande = (index: number) => !!chiffrage.value?.acompte && !!chiffrage.value.lignes[index]?.a_la_demande
</script>

<template>
  <section class="conteneur panier">
    <h1>Panier</h1>
    <div v-if="reprise" class="alerte alerte-info reprise" role="status">
      <p v-if="reprise.ajoutes">Articles de la commande {{ reprise.reference }} ajoutés : vérifiez tailles et quantités.</p>
      <p v-else>Aucun article de la commande {{ reprise.reference }} n'est encore proposé.</p>
      <template v-if="reprise.ecartes.length">
        <p>Non repris :</p>
        <ul><li v-for="e in reprise.ecartes" :key="e">{{ e }}</li></ul>
      </template>
    </div>
    <p v-if="!monte" class="aide">Chargement du panier…</p>
    <div v-else-if="!lignes.length" class="carte vide">
      <p>Votre panier est vide.</p>
      <NuxtLink to="/" class="bouton">Voir les produits</NuxtLink>
    </div>
    <div v-else class="colonnes">
      <ul class="lignes" aria-label="Articles du panier">
        <li v-for="(ligne, index) in lignes" :key="`${ligne.produit_id}-${ligne.variante_id}-${ligne.personnalisation}`" class="carte ligne">
          <ChartePictogramme :type="ligne.rayon_slug" :taille="52" />
          <div class="infos">
            <NuxtLink :to="`/produits/${ligne.slug}`" class="nom">{{ ligne.nom }}</NuxtLink>
            <span v-if="ligne.variante" class="aide">{{ ligne.variante }}</span>
            <span v-if="ligne.personnalisation" class="aide">Texte : « {{ ligne.personnalisation }} »</span>
            <span v-if="aLaDemande(index)" class="aide">Fait à la demande : compte dans l'acompte</span>
            <span v-if="remarque(index)" class="alerte alerte-erreur remarque">{{ remarque(index) }}</span>
          </div>
          <div class="quantite" role="group" :aria-label="`Quantité de ${ligne.nom}`">
            <button type="button" class="bouton bouton-secondaire" :aria-label="ligne.quantite > 1 ? 'Enlever un' : 'Retirer du panier'" @click="changerQuantite(index, ligne.quantite - 1)">−</button>
            <span aria-live="polite">{{ ligne.quantite }}</span>
            <button type="button" class="bouton bouton-secondaire" aria-label="Ajouter un" @click="changerQuantite(index, ligne.quantite + 1)">+</button>
          </div>
          <strong class="montant">{{ montant(index) !== undefined ? formaterFcfa(montant(index)!) : '…' }}</strong>
          <button type="button" class="bouton bouton-discret retirer" @click="changerQuantite(index, 0)">Retirer</button>
        </li>
      </ul>

      <aside class="carte resume">
        <ChoixLivraison :zones="zones" />
        <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
        <RecapitulatifPrix :chiffrage="chiffrage" :en-cours="enCours" />
        <CodePromo :chiffrage="chiffrage" />
        <NuxtLink
          to="/commande" class="bouton bouton-large"
          :class="{ desactive: !chiffrage?.commandable }"
          :aria-disabled="!chiffrage?.commandable"
          @click="(e: MouseEvent) => { if (!chiffrage?.commandable) e.preventDefault() }"
        >
          Commander
        </NuxtLink>
        <p v-if="chiffrage && !chiffrage.commandable" class="aide">Retirez ou corrigez les articles signalés pour commander.</p>
        <NuxtLink to="/devis" class="bouton bouton-secondaire bouton-large">Devis pour une structure</NuxtLink>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.reprise { display: grid; gap: 4px; margin-bottom: 16px; }
.reprise p, .reprise ul { margin: 0; }
.reprise ul { padding-left: 1.2em; }
.panier { padding-top: 24px; }
.vide { padding: 24px; display: grid; justify-items: start; gap: 8px; }
.colonnes { display: grid; gap: 20px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 360px; align-items: start; } }
.lignes { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.ligne {
  display: grid; gap: 10px 14px; padding: 14px; align-items: center;
  grid-template-columns: auto minmax(0, 1fr) auto; grid-template-areas: 'picto infos infos' 'quantite quantite montant' 'retirer retirer retirer';
}
@media (min-width: 640px) {
  .ligne { grid-template-columns: auto minmax(0, 1fr) auto auto; grid-template-areas: 'picto infos quantite montant' 'picto infos retirer retirer'; }
}
.ligne > :first-child { grid-area: picto; }
.infos { grid-area: infos; display: grid; gap: 2px; }
.nom { color: var(--texte); font-weight: 700; text-decoration: none; }
.remarque { margin: 6px 0 0; padding: 0.4em 0.7em; font-size: 0.9rem; }
.quantite { grid-area: quantite; display: flex; align-items: center; gap: 10px; }
.quantite .bouton { min-height: 40px; width: 40px; padding: 0; font-size: 1.2rem; }
.quantite span { min-width: 2ch; text-align: center; font-weight: 700; }
.montant { grid-area: montant; text-align: right; white-space: nowrap; }
.retirer { grid-area: retirer; justify-self: end; min-height: 36px; font-size: 0.9rem; }
.resume { padding: 18px; display: grid; gap: 12px; position: sticky; top: 84px; }
.desactive { opacity: 0.5; pointer-events: auto; cursor: not-allowed; }
</style>
