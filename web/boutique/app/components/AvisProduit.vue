<script setup lang="ts">
import type { AvisPublic, PageAvis } from '~/types/avis'
import { formaterNote } from '~/types/avis'

// Avis publiés sur la fiche produit : synthèse, répartition des notes, puis les avis.
const props = defineProps<{ slug: string, page: PageAvis }>()
const { appeler } = useApiBoutique()
const avis = ref<AvisPublic[]>([...props.page.elements])
const numero = ref(props.page.page)
const chargement = ref(false)
const erreur = ref('')
const reste = computed(() => props.page.nombre - avis.value.length)

async function suite() {
  chargement.value = true
  erreur.value = ''
  try {
    const page = await appeler<PageAvis>(`/api/v1/produits/${props.slug}/avis`, {
      query: { page: numero.value + 1, par_page: props.page.par_page },
    })
    avis.value.push(...page.elements)
    numero.value = page.page
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}
</script>

<template>
  <section id="avis" class="avis" aria-labelledby="titre-avis">
    <h2 id="titre-avis">Avis clients</h2>
    <div v-if="page.nombre && page.moyenne" class="synthese">
      <div class="moyenne">
        <p><strong>{{ formaterNote(page.moyenne) }}</strong> / 5</p>
        <NoteEtoiles :note="page.moyenne" :taille="22" />
        <p class="aide">{{ page.nombre }} avis de clients livrés</p>
      </div>
      <ul class="repartition" aria-label="Répartition des notes">
        <li v-for="note in [5, 4, 3, 2, 1]" :key="note">
          <span>{{ note }} étoile{{ note > 1 ? 's' : '' }}</span>
          <span class="barre" aria-hidden="true"><span :style="{ width: `${((page.repartition[note] ?? 0) / page.nombre) * 100}%` }" /></span>
          <span class="compte">{{ page.repartition[note] ?? 0 }}</span>
        </li>
      </ul>
    </div>
    <p v-else class="aide">Pas encore d'avis sur ce produit.</p>

    <ul v-if="avis.length" class="liste">
      <li v-for="a in avis" :key="a.id" class="un-avis">
        <div class="entete-avis">
          <NoteEtoiles :note="a.note" />
          <strong>{{ a.auteur }}</strong>
          <span class="verifie">Achat vérifié</span>
          <time :datetime="a.date" class="aide">{{ formaterDate(a.date) }}</time>
        </div>
        <p class="texte">{{ a.texte }}</p>
        <div v-if="a.reponse" class="reponse">
          <strong>Réponse de Bibou</strong>
          <p class="texte">{{ a.reponse }}</p>
        </div>
      </li>
    </ul>
    <button v-if="reste > 0" type="button" class="bouton bouton-secondaire" :disabled="chargement" @click="suite">
      Voir plus d'avis ({{ reste }})
    </button>
    <p v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</p>
    <p class="aide">
      Seuls les clients qui ont reçu ce produit peuvent le noter, depuis le suivi de leur commande.
      Chaque avis est relu par notre équipe avant d'être publié.
    </p>
  </section>
</template>

<style scoped>
.avis { margin-top: 40px; display: grid; gap: 16px; max-width: 860px; }
.avis h2 { margin: 0; }
.synthese { display: grid; gap: 20px; padding: 18px; border-radius: var(--rayon); background: var(--fond-doux); }
@media (min-width: 640px) { .synthese { grid-template-columns: auto 1fr; align-items: center; } }
.moyenne { display: grid; gap: 4px; justify-items: start; }
.moyenne p { margin: 0; }
.moyenne strong { font-size: 2.2rem; line-height: 1; }
.repartition { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.repartition li { display: grid; grid-template-columns: 5.5em 1fr 2em; gap: 10px; align-items: center; font-size: 0.92rem; }
.barre { height: 8px; border-radius: 999px; background: var(--etoile-vide); overflow: hidden; }
.barre span { display: block; height: 100%; background: var(--etoile); border-radius: 999px; }
.compte { text-align: right; color: var(--texte-doux); }
.liste { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.un-avis { padding: 14px 0; border-bottom: 1px solid var(--bordure); display: grid; gap: 6px; }
.entete-avis { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
.verifie { font-size: 0.8rem; font-weight: 700; color: var(--succes, #1a7f45); }
.texte { margin: 0; white-space: pre-line; }
.reponse { margin-left: 12px; padding: 8px 12px; border-left: 3px solid var(--primaire); background: var(--primaire-clair); border-radius: 0 8px 8px 0; }
.reponse p { margin: 2px 0 0; }
</style>
