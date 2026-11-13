<script setup lang="ts">
import type { ARecommander, Commande } from '~/types/commandes'
import { classeStatut } from '~/types/commandes'

const route = useRoute()
const reference = String(route.params.reference).toUpperCase()
const cle = ref(typeof route.query.cle === 'string' ? route.query.cle : '')
const nouvelle = route.query.nouvelle === '1'
const retourPaiement = route.query.paiement === 'retour'
useSeoMeta({ title: `Suivi ${reference}`, robots: 'noindex' })

const { appeler, telecharger, url } = useApiBoutique()
const { attendre } = useSession()
const commande = ref<Commande | null>(null)
const erreur = ref('')
const chargement = ref(true)
const action = ref<'annulation' | 'acceptation' | null>(null)
const confirmerAnnulation = ref(false)
const copie = ref(false)
const { ajouter, reprise } = usePanier()
const retrait = useRuntimeConfig().public // adresse et horaires de la boutique, s'ils sont connus
const reprendre = ref(false)

// Les mêmes articles dans le panier : le serveur dit ce qui est encore proposé.
async function commanderANouveau() {
  reprendre.value = true
  try {
    const resultat = await appeler<ARecommander>(`${base.value}/a-recommander`, { query: requete.value })
    resultat.lignes.forEach(ajouter)
    reprise.value = { reference, ajoutes: resultat.lignes.length, ecartes: resultat.ecartes }
    await navigateTo('/panier')
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    reprendre.value = false
  }
}

// Avec la clé du lien : suivi public. Sans clé : commande du compte connecté.
const base = computed(() => cle.value ? `/api/v1/suivi/${reference}` : `/api/v1/mes-commandes/${reference}`)
const requete = computed(() => cle.value ? { cle: cle.value } : undefined)
const lienSuivi = computed(() => (import.meta.client && cle.value ? `${window.location.origin}/suivi/${reference}?cle=${cle.value}` : ''))
const partage = computed(() => `https://wa.me/?text=${encodeURIComponent(`Suivi de ma commande Bibou ${reference} : ${lienSuivi.value}`)}`)

/** Retour de la page de paiement : l'onglet a gardé la clé du lien de suivi. */
function cleDeCetOnglet(): string {
  try {
    return sessionStorage.getItem(`bibou:suivi:${reference}`) ?? ''
  } catch {
    return ''
  }
}

async function charger() {
  chargement.value = true
  try {
    if (!cle.value) cle.value = cleDeCetOnglet()
    if (!cle.value) await attendre()
    commande.value = await appeler<Commande>(base.value, { query: requete.value })
  } catch (e) {
    const statut = (e as { status?: number }).status
    erreur.value = statut === 404 || statut === 401
      ? retourPaiement
        ? 'Votre paiement est en cours de vérification : vous recevrez un SMS dès qu\'il est confirmé. Ouvrez le lien de suivi reçu par SMS pour voir votre commande.'
        : 'Commande introuvable. Ouvrez le lien de suivi reçu, ou connectez-vous avec le compte qui a passé la commande.'
      : messageErreur(e)
  } finally {
    chargement.value = false
  }
}

async function recharger() {
  try {
    commande.value = await appeler<Commande>(base.value, { query: requete.value })
  } catch {
    // la page garde l'état affiché ; le SMS de confirmation suivra
  }
}

async function agir(nom: 'annulation' | 'acceptation') {
  action.value = nom
  erreur.value = ''
  try {
    commande.value = await appeler<Commande>(`${base.value}/${nom}`, { method: 'POST', query: requete.value })
    confirmerAnnulation.value = false
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    action.value = null
  }
}

async function telechargerDocument(nature: 'devis' | 'facture') {
  if (cle.value) window.location.href = url(`/api/v1/suivi/${reference}/${nature}.pdf?cle=${encodeURIComponent(cle.value)}`)
  else await telecharger(`/api/v1/mes-commandes/${reference}/${nature}.pdf`, `${nature}-${reference}.pdf`)
}

async function copier() {
  try {
    await navigator.clipboard.writeText(lienSuivi.value)
    copie.value = true
  } catch {
    copie.value = false
  }
}

onMounted(charger)
</script>

<template>
  <section class="conteneur suivi">
    <p v-if="chargement" class="aide">Chargement de la commande…</p>
    <div v-else-if="!commande" class="carte bloc">
      <h1>Suivi de commande</h1>
      <p class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
      <NuxtLink :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="bouton">Se connecter</NuxtLink>
    </div>
    <template v-else>
      <div v-if="nouvelle" class="carte merci" role="status">
        <h1 v-if="commande.est_devis">Demande de devis {{ commande.reference }} envoyée</h1>
        <h1 v-else>Merci, commande {{ commande.reference }} enregistrée</h1>
        <p v-if="commande.est_devis">Nous préparons votre devis et vous appelons au {{ formaterTelephone(commande.telephone) }}.</p>
        <p v-else-if="commande.acompte">
          Nous vous appelons au {{ formaterTelephone(commande.telephone) }} pour la confirmer. Ensuite, un acompte de
          {{ formaterFcfa(commande.acompte) }} (non remboursable) lance la fabrication de vos articles faits à la demande.
        </p>
        <p v-else>Nous vous appelons au {{ formaterTelephone(commande.telephone) }} pour la confirmer. Rien à payer avant la livraison.</p>
        <template v-if="cle">
          <p class="aide">Ce lien permet de suivre votre commande. Gardez-le, ou envoyez-le-vous sur WhatsApp.</p>
          <div class="partage">
            <button type="button" class="bouton bouton-secondaire" @click="copier">{{ copie ? 'Lien copié' : 'Copier le lien' }}</button>
            <a :href="partage" target="_blank" rel="noopener" class="bouton bouton-secondaire">Envoyer sur WhatsApp</a>
          </div>
        </template>
      </div>

      <div class="entete-suivi">
        <h1 v-if="!nouvelle">{{ commande.est_devis ? 'Devis' : 'Commande' }} {{ commande.reference }}</h1>
        <span :class="classeStatut(commande.statut)">{{ commande.statut_libelle }}</span>
      </div>
      <p v-if="commande.date_promise && !['livree', 'annulee'].includes(commande.statut)" class="promesse">
        {{ commande.mode_livraison === 'livraison' ? 'Livraison prévue' : 'Prête' }} vers le {{ formaterDate(commande.date_promise) }}
      </p>
      <p v-if="commande.statut === 'prete' && commande.mode_livraison === 'retrait' && (retrait.adresse || retrait.horaires)" class="alerte alerte-succes">
        Votre commande vous attend à la boutique<template v-if="retrait.adresse">&nbsp;: {{ retrait.adresse }}</template>.
        <template v-if="retrait.horaires"><br>{{ retrait.horaires }}.</template>
      </p>
      <p v-if="commande.statut === 'acompte_attendu'" class="alerte alerte-info">
        Acompte à régler : <strong>{{ formaterFcfa(commande.acompte_restant) }}</strong>. La fabrication commence dès sa
        réception : payez-le en ligne ou à la boutique. Il n'est pas remboursable si vous annulez ensuite.
        <NuxtLink to="/conditions#acompte">Conditions</NuxtLink>
      </p>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>

      <div class="colonnes">
        <div class="carte bloc">
          <h2>Articles</h2>
          <DetailCommande :commande="commande" />
          <button
            v-if="!commande.est_devis && ['livree', 'annulee'].includes(commande.statut)" type="button"
            class="bouton bouton-secondaire" :disabled="reprendre" @click="commanderANouveau"
          >
            {{ reprendre ? 'Préparation du panier…' : 'Commander à nouveau' }}
          </button>
        </div>
        <aside class="carte bloc">
          <template v-if="commande.devis_disponible">
            <h2>Devis</h2>
            <p v-if="commande.devis_valable_jusqu_au" class="aide">Valable jusqu'au {{ formaterDate(commande.devis_valable_jusqu_au) }}</p>
            <button type="button" class="bouton bouton-secondaire bouton-large" @click="telechargerDocument('devis')">Télécharger le devis (PDF)</button>
            <button v-if="commande.peut_accepter" type="button" class="bouton bouton-large" :disabled="action !== null" @click="agir('acceptation')">
              Accepter le devis
            </button>
          </template>
          <p v-if="commande.statut === 'en_livraison' && commande.livreur_nom" class="livreur">
            Votre livreur : <strong>{{ commande.livreur_nom }}</strong>
            <a v-if="commande.livreur_telephone" :href="`tel:${commande.livreur_telephone}`">{{ formaterTelephone(commande.livreur_telephone) }}</a>
          </p>
          <button v-if="commande.facture" type="button" class="bouton bouton-secondaire bouton-large" @click="telechargerDocument('facture')">
            Télécharger la facture {{ commande.facture }}
          </button>
          <PaiementMobile :commande="commande" :base="base" :requete="requete" :cle="cle" @paye="recharger" />
          <h2>Étapes</h2>
          <HistoriqueCommande :evenements="commande.historique" />
          <template v-if="commande.peut_annuler">
            <button v-if="!confirmerAnnulation" type="button" class="bouton bouton-discret" @click="confirmerAnnulation = true">
              {{ commande.est_devis ? 'Annuler la demande' : 'Annuler la commande' }}
            </button>
            <div v-else class="alerte alerte-info">
              <p>Confirmer l'annulation de {{ commande.reference }} ?</p>
              <p v-if="commande.acompte && commande.montant_paye">
                Les {{ formaterFcfa(Math.min(commande.montant_paye, commande.acompte)) }} déjà payés sont l'acompte d'un
                article fait à la demande : ils ne vous seront pas rendus.
              </p>
              <div class="partage">
                <button type="button" class="bouton" :disabled="action !== null" @click="agir('annulation')">Oui, annuler</button>
                <button type="button" class="bouton bouton-secondaire" @click="confirmerAnnulation = false">Non</button>
              </div>
            </div>
          </template>
        </aside>
      </div>
      <AvisCommande v-if="commande.statut === 'livree'" class="carte" :base="base" :requete="requete" />
    </template>
  </section>
</template>

<style scoped>
.suivi { padding-top: 24px; }
.bloc { padding: 20px; display: grid; gap: 12px; align-content: start; }
.bloc h2 { margin: 0; font-size: 1.1rem; }
.merci { padding: 20px; margin-bottom: 20px; border-color: var(--primaire); }
.merci h1 { font-size: 1.5rem; }
.partage { display: flex; flex-wrap: wrap; gap: 8px; }
.entete-suivi { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 8px; }
.entete-suivi h1 { margin: 0; }
.promesse { font-weight: 650; }
.livreur { padding: 10px 12px; border-radius: 10px; background: var(--primaire-clair); display: grid; gap: 2px; }
.colonnes { display: grid; gap: 20px; }
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 360px; align-items: start; } }
</style>
