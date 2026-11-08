<script setup lang="ts">
import type { ArretLivraison, Livreur } from '~/types/commandes'

useSeoMeta({ title: 'Livraisons', robots: 'noindex' })
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const arrets = ref<ArretLivraison[]>([])
const livreurs = ref<Livreur[]>([])
const choix = reactive<Record<string, string>>({})
const nouveau = reactive({ nom: '', telephone: '' })
const erreur = ref('')
const envoi = ref(false)

const actifs = computed(() => livreurs.value.filter(l => l.est_actif))
const aLivrer = computed(() => grouper(arrets.value.filter(a => a.statut === 'prete'), a => a.zone_nom ?? 'Sans zone'))
const enRoute = computed(() => grouper(arrets.value.filter(a => a.statut === 'en_livraison'), a => a.livreur_nom ?? 'Livreur non indiqué'))
const total = (liste: ArretLivraison[]) => liste.reduce((s, a) => s + a.reste_a_payer, 0)

function grouper(liste: ArretLivraison[], cle: (a: ArretLivraison) => string) {
  const groupes = new Map<string, ArretLivraison[]>()
  for (const a of liste) groupes.set(cle(a), [...(groupes.get(cle(a)) ?? []), a])
  return [...groupes.entries()]
}

async function charger() {
  if (!autorise.value) return
  try {
    const [a, l] = await Promise.all([
      appeler<ArretLivraison[]>('/api/v1/admin/livraisons'),
      appeler<Livreur[]>('/api/v1/admin/livreurs'),
    ])
    arrets.value = a
    livreurs.value = l
    erreur.value = ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function action(reference: string, statut: string, livreurId: string | null = null) {
  if (statut === 'en_livraison' && !livreurId) {
    erreur.value = `Choisissez le livreur de ${reference}.`
    return
  }
  envoi.value = true
  try {
    await appeler(`/api/v1/admin/commandes/${reference}/statut`, {
      method: 'POST',
      body: { statut, livreur_id: livreurId, note: statut === 'prete' ? 'Livraison manquée, retour en boutique' : '' },
    })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function ajouterLivreur() {
  try {
    await appeler('/api/v1/admin/livreurs', { method: 'POST', body: { ...nouveau } })
    nouveau.nom = ''
    nouveau.telephone = ''
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

async function basculer(livreur: Livreur) {
  try {
    await appeler(`/api/v1/admin/livreurs/${livreur.id}`, { method: 'PATCH', body: { est_actif: !livreur.est_actif } })
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function imprimer() {
  window.print()
}

watch(verifie, charger)
</script>

<template>
  <section class="conteneur livraisons">
    <AccesEquipe>
      <div class="entete-livraisons">
        <h1>Livraisons</h1>
        <button type="button" class="bouton bouton-secondaire non-imprime" @click="imprimer">Imprimer la feuille de route</button>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>

      <h2>À livrer</h2>
      <p v-if="!aLivrer.length" class="aide">Aucune commande prête à livrer.</p>
      <section v-for="[zone, liste] in aLivrer" :key="zone" class="groupe">
        <h3>{{ zone }} <small>{{ liste.length }} commande{{ liste.length > 1 ? 's' : '' }}, {{ formaterFcfa(total(liste)) }} à encaisser</small></h3>
        <article v-for="a in liste" :key="a.reference" class="carte arret">
          <div class="infos">
            <NuxtLink :to="`/gestion/commandes/${a.reference}`" class="ref">{{ a.reference }}</NuxtLink>
            <strong>{{ a.client }}</strong>
            <a :href="`tel:${a.telephone}`">{{ formaterTelephone(a.telephone) }}</a>
            <span>{{ a.adresse }}</span>
            <span class="aide">{{ a.nombre_articles }} article{{ a.nombre_articles > 1 ? 's' : '' }}<template v-if="a.date_promise">, promis le {{ formaterDate(a.date_promise) }}</template></span>
          </div>
          <div class="encaisser"><span class="aide">À encaisser</span><strong>{{ formaterFcfa(a.reste_a_payer) }}</strong></div>
          <div class="actions non-imprime">
            <select v-model="choix[a.reference]" :aria-label="`Livreur pour ${a.reference}`">
              <option :value="undefined" disabled>Livreur…</option>
              <option v-for="l in actifs" :key="l.id" :value="l.id">{{ l.nom }}</option>
            </select>
            <button type="button" class="bouton" :disabled="envoi" @click="action(a.reference, 'en_livraison', choix[a.reference] ?? null)">Remettre au livreur</button>
          </div>
        </article>
      </section>

      <h2>En route</h2>
      <p v-if="!enRoute.length" class="aide">Aucune livraison en cours.</p>
      <section v-for="[livreur, liste] in enRoute" :key="livreur" class="groupe">
        <h3>{{ livreur }} <small>{{ liste.length }} arrêt{{ liste.length > 1 ? 's' : '' }}, {{ formaterFcfa(total(liste)) }} à rapporter</small></h3>
        <article v-for="a in liste" :key="a.reference" class="carte arret">
          <div class="infos">
            <NuxtLink :to="`/gestion/commandes/${a.reference}`" class="ref">{{ a.reference }}</NuxtLink>
            <strong>{{ a.client }}</strong>
            <a :href="`tel:${a.telephone}`">{{ formaterTelephone(a.telephone) }}</a>
            <span>{{ a.zone_nom }}, {{ a.adresse }}</span>
          </div>
          <div class="encaisser"><span class="aide">À encaisser</span><strong>{{ formaterFcfa(a.reste_a_payer) }}</strong></div>
          <div class="actions non-imprime">
            <button type="button" class="bouton" :disabled="envoi" @click="action(a.reference, 'livree')">Livrée</button>
            <button type="button" class="bouton bouton-secondaire" :disabled="envoi" @click="action(a.reference, 'prete')">Livraison manquée</button>
          </div>
        </article>
      </section>

      <section class="carte livreurs non-imprime">
        <h2>Livreurs</h2>
        <ul>
          <li v-for="l in livreurs" :key="l.id" :class="{ inactif: !l.est_actif }">
            <span>{{ l.nom }}, {{ formaterTelephone(l.telephone) }}</span>
            <button type="button" class="bouton bouton-discret" @click="basculer(l)">{{ l.est_actif ? 'Désactiver' : 'Réactiver' }}</button>
          </li>
        </ul>
        <form class="ajout" @submit.prevent="ajouterLivreur">
          <input v-model="nouveau.nom" aria-label="Nom du livreur" placeholder="Nom" required minlength="2">
          <input v-model="nouveau.telephone" aria-label="Téléphone du livreur" type="tel" placeholder="Téléphone" required>
          <button type="submit" class="bouton bouton-secondaire">Ajouter</button>
        </form>
      </section>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.livraisons { padding-top: 20px; }
.entete-livraisons { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.entete-livraisons h1 { margin: 0; }
.groupe { display: grid; gap: 10px; margin-bottom: 20px; }
.groupe h3 { margin: 0; font-size: 1.05rem; }
.groupe h3 small { color: var(--texte-doux); font-weight: 500; margin-left: 6px; }
.arret { padding: 14px 16px; display: grid; gap: 10px; grid-template-columns: 1fr auto; }
.infos { display: grid; gap: 2px; }
.ref { font-weight: 800; text-decoration: none; }
.encaisser { text-align: right; display: grid; align-content: start; }
.encaisser strong { font-size: 1.15rem; color: var(--primaire); }
.actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
.actions select { min-height: 46px; padding: 0 10px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; flex: 1; min-width: 160px; }
.livreurs { padding: 18px; margin-top: 12px; }
.livreurs h2 { margin: 0 0 8px; font-size: 1.1rem; }
.livreurs ul { list-style: none; margin: 0 0 12px; padding: 0; display: grid; gap: 4px; }
.livreurs li { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.livreurs li.inactif span { color: var(--texte-doux); text-decoration: line-through; }
.ajout { display: flex; flex-wrap: wrap; gap: 8px; }
.ajout input { flex: 1; min-width: 140px; min-height: 44px; padding: 0 10px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; }
@media print {
  .non-imprime { display: none !important; }
  .arret { break-inside: avoid; box-shadow: none; }
}
</style>
