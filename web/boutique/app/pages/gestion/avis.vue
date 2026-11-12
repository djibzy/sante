<script setup lang="ts">
import type { AvisGestion, PageAvisGestion, StatutAvis } from '~/types/avis'

useSeoMeta({ title: 'Avis clients', robots: 'noindex' })
const ONGLETS: { cle: StatutAvis, titre: string }[] = [
  { cle: 'en_attente', titre: 'À relire' },
  { cle: 'publie', titre: 'Publiés' },
  { cle: 'refuse', titre: 'Refusés' },
]
const MOTIFS = [
  'Merci de ne mentionner aucune information médicale (maladie, traitement).',
  "Merci de ne mentionner ni nom complet ni numéro de téléphone.",
  "Votre avis ne porte pas sur l'article reçu : écrivez-nous sur WhatsApp pour toute autre question.",
]
const route = useRoute()
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const onglet = computed(() => ONGLETS.find(o => o.cle === route.query.statut) ?? ONGLETS[0]!)
const resultat = ref<PageAvisGestion | null>(null)
const erreur = ref('')
const envoi = ref<string | null>(null)
const saisies = reactive<Record<string, { reponse: string, motif: string, refus: boolean }>>({})

async function charger() {
  if (!autorise.value) return
  try {
    resultat.value = await appeler<PageAvisGestion>('/api/v1/admin/avis', { query: { statut: onglet.value.cle } })
    for (const a of resultat.value.elements) saisies[a.id] = { reponse: a.reponse ?? '', motif: '', refus: false }
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function decider(avis: AvisGestion, decision: 'publier' | 'refuser') {
  const saisie = saisies[avis.id]!
  envoi.value = avis.id
  erreur.value = ''
  try {
    await appeler<AvisGestion>(`/api/v1/admin/avis/${avis.id}/moderation`, {
      method: 'POST',
      body: { decision, motif: decision === 'refuser' ? saisie.motif : null, reponse: saisie.reponse || null },
    })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = null
  }
}

watch([verifie, () => route.query.statut], charger)
</script>

<template>
  <section class="conteneur gestion">
    <AccesEquipe>
      <h1>Avis clients</h1>
      <p class="aide consigne">
        Publiez les avis sur les articles. Refusez ceux qui mentionnent une maladie, un traitement,
        un nom complet ou un numéro de téléphone, ou qui sont injurieux : le motif est montré au client,
        qui peut réécrire son avis.
      </p>
      <nav class="onglets" aria-label="Filtrer les avis">
        <NuxtLink
          v-for="o in ONGLETS" :key="o.cle" :to="{ query: { statut: o.cle } }"
          class="onglet" :class="{ actif: o.cle === onglet.cle }" :aria-current="o.cle === onglet.cle ? 'page' : undefined"
        >{{ o.titre }}<template v-if="o.cle === onglet.cle && resultat"> ({{ resultat.total }})</template></NuxtLink>
      </nav>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <p v-if="resultat && !resultat.elements.length" class="aide">Aucun avis ici pour le moment.</p>
      <ul v-if="resultat" class="avis-equipe">
        <li v-for="a in resultat.elements" :key="a.id" class="carte un-avis">
          <div class="entete-avis">
            <NoteEtoiles :note="a.note" :taille="18" />
            <strong>{{ a.auteur }}</strong>
            <NuxtLink :to="`/produits/${a.produit_slug}`">{{ a.produit_nom }}</NuxtLink>
            <NuxtLink :to="`/gestion/commandes/${a.commande_reference}`" class="aide">{{ a.commande_reference }}</NuxtLink>
            <span class="aide">{{ formaterDateHeure(a.cree_le) }}</span>
          </div>
          <p class="texte">{{ a.texte }}</p>
          <p v-if="a.statut === 'refuse'" class="alerte alerte-info">Motif donné au client : {{ a.motif_refus }}</p>
          <div class="champ">
            <label :for="`reponse-${a.id}`">Réponse publiée avec l'avis (facultatif)</label>
            <textarea :id="`reponse-${a.id}`" v-model="saisies[a.id]!.reponse" rows="2" maxlength="1000" />
          </div>
          <div v-if="saisies[a.id]!.refus" class="champ">
            <label :for="`motif-${a.id}`">Motif, montré au client</label>
            <input :id="`motif-${a.id}`" v-model="saisies[a.id]!.motif" maxlength="200" :list="`motifs-${a.id}`" required>
            <datalist :id="`motifs-${a.id}`"><option v-for="m in MOTIFS" :key="m" :value="m" /></datalist>
          </div>
          <div class="actions">
            <button
              v-if="a.statut !== 'publie' || saisies[a.id]!.reponse !== (a.reponse ?? '')" type="button" class="bouton"
              :disabled="envoi === a.id" @click="decider(a, 'publier')"
            >{{ a.statut === 'publie' ? 'Enregistrer la réponse' : 'Publier' }}</button>
            <button
              v-if="!saisies[a.id]!.refus && a.statut !== 'refuse'" type="button" class="bouton bouton-secondaire"
              @click="saisies[a.id]!.refus = true"
            >{{ a.statut === 'publie' ? 'Retirer' : 'Refuser' }}</button>
            <button
              v-if="saisies[a.id]!.refus" type="button" class="bouton bouton-secondaire"
              :disabled="envoi === a.id || !saisies[a.id]!.motif.trim()" @click="decider(a, 'refuser')"
            >Confirmer le refus</button>
          </div>
        </li>
      </ul>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.gestion { padding-top: 20px; }
.consigne { max-width: 760px; }
.onglets { display: flex; gap: 6px; overflow-x: auto; margin: 16px 0; padding-bottom: 4px; }
.onglet { padding: 8px 14px; border-radius: 999px; text-decoration: none; color: var(--texte); background: var(--fond-doux); white-space: nowrap; font-weight: 600; }
.onglet.actif { background: var(--primaire); color: #fff; }
.avis-equipe { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; max-width: 860px; }
.un-avis { padding: 16px; display: grid; gap: 10px; }
.entete-avis { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
.texte { margin: 0; white-space: pre-line; }
.un-avis .alerte { margin: 0; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
