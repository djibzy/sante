<script setup lang="ts">
import type { AvisClient, AvisCommande, ProduitAEvaluer } from '~/types/avis'

// Commande reçue : le client note chaque article. L'avis est relu par l'équipe avant publication.
const props = defineProps<{ base: string, requete?: Record<string, string> }>()
const { appeler } = useApiBoutique()
const adresse = useAdresseImage()
const donnees = ref<AvisCommande | null>(null)
const brouillons = reactive<Record<string, { note: number, texte: string }>>({})
const envoi = ref<string | null>(null)
const erreurs = reactive<Record<string, string>>({})
const merci = reactive<Record<string, boolean>>({})

async function charger() {
  try {
    donnees.value = await appeler<AvisCommande>(`${props.base}/avis`, { query: props.requete })
    for (const p of donnees.value.produits) {
      brouillons[p.produit_id] ??= { note: p.avis?.note ?? 0, texte: p.avis?.texte ?? '' }
    }
  } catch {
    donnees.value = null // le reste du suivi reste utilisable
  }
}

async function envoyer(produit: ProduitAEvaluer) {
  const brouillon = brouillons[produit.produit_id]!
  erreurs[produit.produit_id] = ''
  if (!brouillon.note) {
    erreurs[produit.produit_id] = 'Choisissez une note de 1 à 5 étoiles.'
    return
  }
  envoi.value = produit.produit_id
  try {
    produit.avis = await appeler<AvisClient>(`${props.base}/avis`, {
      method: 'POST', query: props.requete,
      body: { produit_id: produit.produit_id, note: brouillon.note, texte: brouillon.texte },
    })
    merci[produit.produit_id] = true
  } catch (e) {
    erreurs[produit.produit_id] = messageErreur(e)
  } finally {
    envoi.value = null
  }
}

onMounted(charger)
</script>

<template>
  <section v-if="donnees?.possible" class="avis-commande" aria-labelledby="titre-avis-commande">
    <h2 id="titre-avis-commande">Votre avis sur les articles reçus</h2>
    <p class="aide">
      Aidez les autres soignants à choisir. Votre avis est publié avec votre prénom et l'initiale de
      votre nom, après relecture par notre équipe. N'indiquez aucune information médicale.
    </p>
    <article v-for="p in donnees.produits" :key="p.produit_id" class="article-a-noter">
      <div class="entete-article">
        <img v-if="p.image" :src="adresse(p.image.url)" alt="" width="48" height="60" loading="lazy">
        <NuxtLink :to="`/produits/${p.slug}`">{{ p.nom }}</NuxtLink>
      </div>
      <template v-if="p.avis?.statut === 'publie'">
        <p class="publie"><NoteEtoiles :note="p.avis.note" /> Avis publié, merci !</p>
        <p class="texte">{{ p.avis.texte }}</p>
        <p v-if="p.avis.reponse" class="aide">Réponse de Bibou : {{ p.avis.reponse }}</p>
      </template>
      <form v-else class="formulaire-avis" @submit.prevent="envoyer(p)">
        <p v-if="p.avis?.statut === 'en_attente'" class="alerte alerte-succes" role="status">
          {{ merci[p.produit_id] ? 'Merci ! ' : '' }}Votre avis sera publié après relecture. Vous pouvez encore le modifier.
        </p>
        <p v-else-if="p.avis?.statut === 'refuse'" class="alerte alerte-erreur">
          Votre avis n'a pas été publié : {{ p.avis.motif_refus }} Vous pouvez le réécrire.
        </p>
        <ChoixNote v-model="brouillons[p.produit_id]!.note" :nom="`note-${p.produit_id}`" legende="Votre note" />
        <div class="champ">
          <label :for="`texte-${p.produit_id}`">Votre avis</label>
          <textarea
            :id="`texte-${p.produit_id}`" v-model="brouillons[p.produit_id]!.texte" rows="3"
            minlength="10" maxlength="1000" required placeholder="Taille, tissu, broderie, tenue au lavage…"
          />
        </div>
        <p v-if="erreurs[p.produit_id]" class="alerte alerte-erreur" role="alert">{{ erreurs[p.produit_id] }}</p>
        <button type="submit" class="bouton" :disabled="envoi === p.produit_id">
          {{ p.avis ? 'Modifier mon avis' : 'Envoyer mon avis' }}
        </button>
      </form>
    </article>
  </section>
</template>

<style scoped>
.avis-commande { display: grid; gap: 14px; margin-top: 20px; padding: 20px; }
.avis-commande h2 { margin: 0; font-size: 1.2rem; }
.avis-commande > .aide { margin: 0; }
.article-a-noter { display: grid; gap: 10px; padding-top: 14px; border-top: 1px solid var(--bordure); }
.entete-article { display: flex; align-items: center; gap: 12px; font-weight: 650; }
.entete-article img { width: 48px; height: 60px; object-fit: cover; border-radius: 8px; }
.formulaire-avis { display: grid; gap: 10px; justify-items: start; }
.formulaire-avis .champ { width: 100%; }
.formulaire-avis .alerte { margin: 0; }
.publie { display: flex; align-items: center; gap: 8px; margin: 0; font-weight: 650; }
.texte { margin: 0; white-space: pre-line; }
</style>
