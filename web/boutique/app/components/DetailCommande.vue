<script setup lang="ts">
import type { Commande } from '~/types/commandes'

// Articles, montants et réception : commun au suivi du client et à la gestion.
defineProps<{ commande: Commande }>()
</script>

<template>
  <div class="detail">
    <table class="articles">
      <caption class="visuellement-cache">Articles</caption>
      <thead>
        <tr><th scope="col">Article</th><th scope="col">Qté</th><th scope="col">Montant</th></tr>
      </thead>
      <tbody>
        <tr v-for="ligne in commande.lignes" :key="ligne.id">
          <td>
            {{ ligne.libelle }}
            <span v-if="ligne.personnalisation" class="aide">Texte : « {{ ligne.personnalisation }} »</span>
            <span class="aide">{{ formaterFcfa(ligne.prix_unitaire) }} l'unité</span>
          </td>
          <td>{{ ligne.quantite }}</td>
          <td>{{ formaterFcfa(ligne.montant) }}</td>
        </tr>
      </tbody>
    </table>
    <dl class="montants">
      <div><dt>Articles</dt><dd>{{ formaterFcfa(commande.sous_total) }}</dd></div>
      <div v-if="commande.remise"><dt>Remise</dt><dd>− {{ formaterFcfa(commande.remise) }}</dd></div>
      <div>
        <dt>{{ commande.mode_livraison === 'livraison' ? `Livraison, ${commande.zone_nom}` : 'Retrait à la boutique' }}</dt>
        <dd>{{ commande.frais_livraison ? formaterFcfa(commande.frais_livraison) : 'Gratuit' }}</dd>
      </div>
      <div class="total"><dt>Total</dt><dd>{{ formaterFcfa(commande.total) }}</dd></div>
      <div v-if="commande.montant_paye"><dt>Déjà payé</dt><dd>{{ formaterFcfa(commande.montant_paye) }}</dd></div>
      <div v-if="commande.montant_paye && commande.reste_a_payer"><dt>Reste à payer</dt><dd>{{ formaterFcfa(commande.reste_a_payer) }}</dd></div>
    </dl>
    <p v-if="commande.mode_livraison === 'livraison' && commande.adresse" class="aide">Adresse : {{ commande.adresse }}</p>
  </div>
</template>

<style scoped>
.articles { width: 100%; border-collapse: collapse; }
.articles th { text-align: left; font-size: 0.85rem; color: var(--texte-doux); font-weight: 600; padding: 0 0 6px; }
.articles td { padding: 10px 0; border-top: 1px solid var(--bordure); vertical-align: top; }
.articles td .aide { display: block; }
.articles th:not(:first-child), .articles td:not(:first-child) { text-align: right; padding-left: 12px; white-space: nowrap; }
.montants { margin: 12px 0 0; display: grid; gap: 4px; }
.montants div { display: flex; justify-content: space-between; gap: 12px; }
.montants dt { color: var(--texte-doux); }
.montants dd { margin: 0; font-weight: 650; white-space: nowrap; }
.montants .total { border-top: 1px solid var(--bordure); padding-top: 8px; margin-top: 4px; }
.montants .total dt { color: var(--texte); font-weight: 700; }
.montants .total dd { color: var(--primaire); font-size: 1.2rem; font-weight: 800; }
</style>
