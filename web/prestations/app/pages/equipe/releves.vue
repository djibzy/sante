<script setup lang="ts">
import type { Synthese } from '~/types/prestations'

// Le mois : ce que doit chaque structure, ce que l'on doit aux partenaires, la marge. Les
// relevés PDF partent aux structures ; le CSV va au comptable.
useSeoMeta({ title: 'Relevés', robots: 'noindex' })
const { appeler, telecharger } = useApiPrestations()
const { verifie, estGestionnaire } = useEquipe()
const mois = ref(moisCourant())
const synthese = ref<Synthese | null>(null)
const erreur = ref('')

async function charger() {
  if (!estGestionnaire.value || !/^\d{4}-\d{2}$/.test(mois.value)) return
  try {
    synthese.value = await appeler<Synthese>(`/api/v1/admin/releves/${mois.value}`)
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function fichier(chemin: string, nom: string) {
  try {
    await telecharger(chemin, nom)
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}
watch([verifie, mois], charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe gestion>
      <div class="entete-page">
        <h1>Relevés <span v-if="synthese" class="aide">{{ synthese.libelle_mois }}</span></h1>
        <div class="boutons">
          <label for="mois" class="visuellement-cache">Mois</label>
          <input id="mois" v-model="mois" type="month" class="mois">
          <button type="button" class="bouton bouton-secondaire" @click="fichier(`/api/v1/admin/releves/${mois}.csv`, `prestations-${mois}.csv`)">Exporter (CSV)</button>
        </div>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <template v-if="synthese">
        <dl class="tuiles">
          <div class="carte"><dt>Montant dû par les structures</dt><dd>{{ formaterFcfa(synthese.chiffre) }}</dd></div>
          <div class="carte"><dt>Coût des partenaires</dt><dd>{{ formaterFcfa(synthese.cout) }}</dd></div>
          <div class="carte"><dt>Marge</dt><dd>{{ formaterFcfa(synthese.marge) }}</dd></div>
          <div class="carte"><dt>Pièces rendues</dt><dd>{{ synthese.pieces_rendues }}</dd></div>
          <div class="carte" :class="{ alerte: synthese.pieces_manquantes }"><dt>Pièces manquantes</dt><dd>{{ synthese.pieces_manquantes }}</dd></div>
          <div class="carte"><dt>Pièces dehors aujourd'hui</dt><dd>{{ synthese.en_cours }}</dd></div>
        </dl>

        <h2>Par structure</h2>
        <p v-if="!synthese.contrats.length" class="aide">Aucun linge rendu ni forfait ce mois-ci.</p>
        <div v-else class="tableau-defilant" tabindex="0" role="region" aria-label="Relevé par structure">
          <table class="tableau">
            <thead>
              <tr>
                <th scope="col">Contrat</th><th scope="col">Structure</th><th scope="col" class="nombre">Collectes</th>
                <th scope="col" class="nombre">Rendues</th><th scope="col" class="nombre">Manquantes</th>
                <th scope="col" class="nombre">Montant dû</th><th scope="col" class="nombre">Coût</th><th scope="col" class="nombre">Marge</th>
                <th scope="col"><span class="visuellement-cache">Relevé</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in synthese.contrats" :key="c.reference">
                <td><NuxtLink :to="`/equipe/contrats/${c.reference}`">{{ c.reference }}</NuxtLink></td>
                <td>
                  {{ c.structure }}
                  <span v-if="c.prix_manquants" class="pastille pastille-danger">Prix à fixer</span>
                  <span v-if="c.cout_incomplet" class="pastille pastille-accent">Coût incomplet</span>
                </td>
                <td class="nombre">{{ c.collectes }}</td>
                <td class="nombre">{{ c.pieces_rendues }}</td>
                <td class="nombre">{{ c.pieces_manquantes || '–' }}</td>
                <td class="nombre">{{ formaterFcfa(c.chiffre) }}</td>
                <td class="nombre">{{ formaterFcfa(c.cout) }}</td>
                <td class="nombre">{{ formaterFcfa(c.marge) }}</td>
                <td>
                  <button type="button" class="bouton bouton-discret" @click="fichier(`/api/v1/admin/contrats/${c.reference}/releves/${mois}.pdf`, `releve-${c.reference}-${mois}.pdf`)">PDF</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="aide">« Prix à fixer » : des articles sans prix au contrat ; ajoutez-les au contrat avant d'envoyer le relevé. « Coût incomplet » : un tarif manque chez le partenaire.</p>

        <h2>Par partenaire</h2>
        <p v-if="!synthese.partenaires.length" class="aide">Aucun linge rendu par un partenaire ce mois-ci.</p>
        <div v-else class="tableau-defilant" tabindex="0" role="region" aria-label="Relevé par partenaire">
          <table class="tableau">
            <thead>
              <tr><th scope="col">Partenaire</th><th scope="col" class="nombre">Collectes</th><th scope="col" class="nombre">Pièces</th><th scope="col" class="nombre">Poids</th><th scope="col" class="nombre">À payer</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in synthese.partenaires" :key="p.id">
                <td>{{ p.nom }} <span v-if="p.cout_incomplet" class="pastille pastille-accent">Coût incomplet</span></td>
                <td class="nombre">{{ p.collectes }}</td>
                <td class="nombre">{{ p.pieces }}</td>
                <td class="nombre">{{ p.mode_tarif === 'kg' ? `${p.poids_kg} kg` : '–' }}</td>
                <td class="nombre">{{ formaterFcfa(p.cout) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </AccesEquipe>
  </section>
</template>

<style scoped>
h1 .aide { font-size: 1rem; font-weight: 500; }
h2 { font-size: 1.2rem; margin-top: 1.6rem; }
.mois { min-height: 46px; border: 1.5px solid var(--bordure); border-radius: 10px; padding: 0 0.6em; font: inherit; }
.tuiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr)); margin: 0; }
.tuiles > div { padding: 14px 16px; }
.tuiles dt { color: var(--texte-doux); font-size: 0.88rem; }
.tuiles dd { margin: 4px 0 0; font-size: 1.35rem; font-weight: 800; font-variant-numeric: tabular-nums; }
.tuiles .alerte { border-color: var(--danger); background: var(--danger-clair); margin: 0; }
.tableau .pastille { margin-left: 4px; }
</style>
