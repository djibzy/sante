<script setup lang="ts">
import type { Collecte, PartenaireResume } from '~/types/prestations'
import { classeCollecte } from '~/types/prestations'

// Bon de collecte : les comptes de chaque étape, à imprimer ou à montrer à la structure.
useSeoMeta({ title: 'Bon de collecte', robots: 'noindex' })
const route = useRoute()
const reference = computed(() => String(route.params.reference))
const { appeler } = useApiPrestations()
const { verifie, autorise, estGestionnaire } = useEquipe()
const collecte = ref<Collecte | null>(null)
const partenaires = ref<PartenaireResume[]>([])
const erreur = ref('')
const message = ref('')
const retour = ref(false)
const motif = ref('')

async function charger() {
  if (!autorise.value) return
  try {
    ;[collecte.value, partenaires.value] = await Promise.all([
      appeler<Collecte>(`/api/v1/collectes/${reference.value}`),
      appeler<PartenaireResume[]>('/api/v1/partenaires'),
    ])
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function mettreAJour(c: Collecte, texte: string) {
  collecte.value = c
  retour.value = false
  message.value = texte
  erreur.value = ''
}

async function agir(chemin: string, body: Record<string, unknown> | undefined, texte: string) {
  try {
    mettreAJour(await appeler<Collecte>(`/api/v1/collectes/${reference.value}/${chemin}`, { method: 'POST', body }), texte)
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

const peutAnnuler = computed(() => collecte.value?.statut === 'prevue'
  || (collecte.value?.statut === 'enlevee' && estGestionnaire.value))
const etapes = computed(() => {
  const c = collecte.value
  if (!c) return []
  return [
    { nom: 'Enlevée', quand: c.enlevee_le, detail: c.remis_par ? `remise par ${c.remis_par}` : '' },
    { nom: 'Déposée chez le partenaire', quand: c.deposee_le, detail: c.partenaire?.nom ?? '' },
    { nom: 'Prête', quand: c.prete_le, detail: '' },
    { nom: 'Rendue', quand: c.rendue_le, detail: c.recu_par ? `reçue par ${c.recu_par}` : '' },
  ].filter(e => e.quand)
})
const imprimer = () => window.print()
watch(verifie, charger)
</script>

<template>
  <section class="conteneur">
    <AccesEquipe>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>
      <article v-if="collecte" class="carte bon">
        <header class="entete-page">
          <h1>Bon {{ collecte.reference }}</h1>
          <span :class="classeCollecte(collecte.statut, collecte.en_retard)">{{ collecte.en_retard ? 'En retard' : collecte.libelle_statut }}</span>
        </header>
        <div class="infos">
          <div>
            <h2>{{ collecte.contrat.structure }}</h2>
            <p>{{ collecte.contrat.adresse }}</p>
            <p>{{ collecte.contrat.contact }} · <a :href="`tel:${collecte.contrat.telephone}`">{{ formaterTelephone(collecte.contrat.telephone) }}</a></p>
          </div>
          <dl>
            <div><dt>Collecte du</dt><dd>{{ formaterDate(collecte.prevue_le) }}</dd></div>
            <div v-if="collecte.retour_prevu_le"><dt>Retour promis</dt><dd>{{ formaterDate(collecte.retour_prevu_le) }}</dd></div>
            <div v-if="collecte.sacs !== null"><dt>Sacs</dt><dd>{{ collecte.sacs }}</dd></div>
            <div v-if="collecte.poids_kg !== null"><dt>Poids au dépôt</dt><dd>{{ collecte.poids_kg }} kg</dd></div>
          </dl>
        </div>

        <div v-if="collecte.lignes.length" class="tableau-defilant" tabindex="0" role="region" aria-label="Pièces comptées">
          <table class="tableau">
            <thead>
              <tr><th scope="col">Article</th><th scope="col" class="nombre">Enlevées</th><th scope="col" class="nombre">Rendues</th><th scope="col" class="nombre">Écart</th></tr>
            </thead>
            <tbody>
              <tr v-for="ligne in collecte.lignes" :key="`${ligne.article}-${ligne.precision}`">
                <th scope="row">{{ ligne.libelle }}</th>
                <td class="nombre">{{ ligne.quantite_enlevee }}</td>
                <td class="nombre">{{ ligne.quantite_rendue ?? '–' }}</td>
                <td class="nombre" :class="{ manque: (ligne.ecart ?? 0) < 0 }">{{ ligne.ecart === null ? '' : ligne.ecart > 0 ? `+${ligne.ecart}` : ligne.ecart || '' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Total</th>
                <td class="nombre">{{ collecte.pieces_enlevees }}</td>
                <td class="nombre">{{ collecte.pieces_rendues ?? '–' }}</td>
                <td class="nombre" :class="{ manque: collecte.pieces_manquantes }">{{ collecte.pieces_manquantes ? `−${collecte.pieces_manquantes}` : '' }}</td>
              </tr>
            </tfoot>
          </table>
        </div>

        <p v-if="collecte.pieces_manquantes" class="alerte alerte-erreur manquantes">
          {{ collecte.pieces_manquantes }} pièce{{ collecte.pieces_manquantes > 1 ? 's' : '' }} manquante{{ collecte.pieces_manquantes > 1 ? 's' : '' }} au retour :
          à rechercher chez le partenaire, puis à remplacer ou rembourser.
        </p>
        <ol v-if="etapes.length" class="etapes">
          <li v-for="e in etapes" :key="e.nom"><strong>{{ e.nom }}</strong> le {{ formaterDateHeure(e.quand!) }}<template v-if="e.detail"> – {{ e.detail }}</template></li>
        </ol>
        <p v-if="collecte.observations"><strong>À l'enlèvement :</strong> {{ collecte.observations }}</p>
        <p v-if="collecte.observations_retour"><strong>Au retour :</strong> {{ collecte.observations_retour }}</p>
        <p v-if="collecte.motif_annulation"><strong>Annulée :</strong> {{ collecte.motif_annulation }}</p>

        <div class="actions">
          <FormulaireDepot
            v-if="collecte.statut === 'enlevee'" :collecte="collecte" :partenaires="partenaires"
            @fait="c => mettreAJour(c, `Déposée chez ${c.partenaire?.nom}.`)"
          />
          <div class="boutons">
            <button v-if="collecte.statut === 'chez_partenaire'" type="button" class="bouton bouton-secondaire" @click="agir('prete', undefined, 'Linge prêt chez le partenaire.')">Prête chez le partenaire</button>
            <button v-if="['chez_partenaire', 'prete'].includes(collecte.statut) && !retour" type="button" class="bouton" @click="retour = true">Rendre et recompter</button>
            <button type="button" class="bouton bouton-discret" @click="imprimer">Imprimer le bon</button>
          </div>
          <FormulaireRetour v-if="retour" :collecte="collecte" @fait="c => mettreAJour(c, 'Linge rendu et recompté.')" @fermer="retour = false" />
          <form v-if="peutAnnuler" class="annuler" @submit.prevent="agir('annulation', { motif }, 'Collecte annulée.')">
            <div class="champ">
              <label for="motif">Annuler cette collecte : pourquoi ?</label>
              <input id="motif" v-model="motif" required minlength="3" maxlength="200" placeholder="Saisie en double, erreur de structure…">
            </div>
            <button type="submit" class="bouton bouton-secondaire">Annuler la collecte</button>
          </form>
        </div>
      </article>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.bon { padding: 16px; display: grid; gap: 14px; }
.bon .tableau { font-size: 0.92rem; }
.manquantes { margin: 0; }
.infos { display: grid; gap: 14px; }
@media (min-width: 720px) { .infos { grid-template-columns: 1.4fr 1fr; } }
.infos h2 { margin: 0 0 4px; font-size: 1.2rem; }
.infos p { margin: 0 0 2px; }
.infos dl { margin: 0; display: grid; gap: 6px; }
.infos dt { color: var(--texte-doux); font-size: 0.85rem; }
.infos dd { margin: 0; font-weight: 650; }
.manque { color: var(--danger); font-weight: 750; }
.etapes { margin: 0; padding-left: 1.2em; display: grid; gap: 4px; }
.bon > p { margin: 0; }
.actions { display: grid; gap: 10px; }
.annuler { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); align-items: end; border-top: 1px solid var(--bordure); padding-top: 12px; }
.annuler .bouton { margin-bottom: 1rem; }
@media print { .actions { display: none; } }
</style>
