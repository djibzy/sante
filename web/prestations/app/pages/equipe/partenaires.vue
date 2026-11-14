<script setup lang="ts">
import type { Offre, Partenaire } from '~/types/prestations'

// Blanchisseries et pressings partenaires : ce qu'ils nous facturent, leur délai, la visite
// d'hygiène. Notre propre blanchisserie, une fois ouverte, s'ajoute ici comme partenaire interne.
useSeoMeta({ title: 'Partenaires', robots: 'noindex' })
const { appeler } = useApiPrestations()
const { verifie, estGestionnaire } = useEquipe()
const partenaires = ref<Partenaire[] | null>(null)
const offre = ref<Offre | null>(null)
const erreur = ref('')
const message = ref('')
const edite = ref<string | null>(null) // id, « nouveau » ou rien

const VIDE = {
  nom: '', type: 'blanchisserie', est_interne: false, contact: '', telephone: '', quartier: '',
  delai_jours: 2, capacite_pieces_jour: null as number | null, mode_tarif: 'piece',
  tarif_kg: null as number | null, hygiene_verifiee_le: '', notes: '', est_actif: true,
}
const fiche = reactive({ ...VIDE })
const tarifs = ref<Record<string, number | null>>({})

async function charger() {
  if (!estGestionnaire.value) return
  try {
    ;[partenaires.value, offre.value] = await Promise.all([
      appeler<Partenaire[]>('/api/v1/admin/partenaires'),
      offre.value ?? appeler<Offre>('/api/v1/offre'),
    ])
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

function editer(p: Partenaire | null) {
  message.value = ''
  erreur.value = ''
  edite.value = p?.id ?? 'nouveau'
  Object.assign(fiche, p
    ? { ...p, hygiene_verifiee_le: p.hygiene_verifiee_le ?? '' }
    : VIDE)
  tarifs.value = p ? { ...p.tarifs } : {}
}

async function enregistrer() {
  const corps = {
    nom: fiche.nom, type: fiche.type, est_interne: fiche.est_interne, contact: fiche.contact,
    telephone: fiche.telephone, quartier: fiche.quartier, delai_jours: fiche.delai_jours,
    capacite_pieces_jour: fiche.capacite_pieces_jour || null, mode_tarif: fiche.mode_tarif,
    tarif_kg: fiche.mode_tarif === 'kg' ? fiche.tarif_kg : null,
    tarifs: Object.fromEntries(Object.entries(tarifs.value).filter(([, prix]) => prix !== null && prix !== undefined)),
    hygiene_verifiee_le: fiche.hygiene_verifiee_le || null, notes: fiche.notes, est_actif: fiche.est_actif,
  }
  try {
    const enregistre = edite.value === 'nouveau'
      ? await appeler<Partenaire>('/api/v1/admin/partenaires', { method: 'POST', body: corps })
      : await appeler<Partenaire>(`/api/v1/admin/partenaires/${edite.value}`, { method: 'PATCH', body: corps })
    message.value = `${enregistre.nom} enregistré.`
    edite.value = null
    await charger()
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
        <h1>Partenaires</h1>
        <button v-if="edite !== 'nouveau'" type="button" class="bouton" @click="editer(null)">Ajouter un partenaire</button>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>

      <form v-if="edite && offre" class="carte fiche" @submit.prevent="enregistrer">
        <h2>{{ edite === 'nouveau' ? 'Nouveau partenaire' : fiche.nom }}</h2>
        <div class="grille-champs">
          <div class="champ"><label for="nom">Nom</label><input id="nom" v-model="fiche.nom" required minlength="2" maxlength="120"></div>
          <div class="champ">
            <label for="type">Type</label>
            <select id="type" v-model="fiche.type"><option value="blanchisserie">Blanchisserie</option><option value="pressing">Pressing</option></select>
          </div>
          <div class="champ"><label for="contact">Contact</label><input id="contact" v-model="fiche.contact" maxlength="120"></div>
          <div class="champ"><label for="tel">Téléphone</label><input id="tel" v-model="fiche.telephone" type="tel" required></div>
          <div class="champ"><label for="quartier">Quartier</label><input id="quartier" v-model="fiche.quartier" maxlength="160"></div>
          <div class="champ"><label for="delai">Délai habituel (jours)</label><input id="delai" v-model.number="fiche.delai_jours" type="number" min="0" max="14" required></div>
          <div class="champ"><label for="capacite">Capacité (pièces par jour)</label><input id="capacite" v-model.number="fiche.capacite_pieces_jour" type="number" min="1"></div>
          <div class="champ"><label for="hygiene">Visite d'hygiène faite le</label><input id="hygiene" v-model="fiche.hygiene_verifiee_le" type="date"></div>
        </div>
        <div class="choix">
          <label><input v-model="fiche.mode_tarif" type="radio" value="piece"> Nous facture à la pièce</label>
          <label><input v-model="fiche.mode_tarif" type="radio" value="kg"> Nous facture au kilo</label>
        </div>
        <div v-if="fiche.mode_tarif === 'kg'" class="champ prix-kg">
          <label for="kg">Prix au kilo (FCFA)</label><input id="kg" v-model.number="fiche.tarif_kg" type="number" min="0" step="25" required>
        </div>
        <GrilleArticles v-else v-model="tarifs" :articles="offre.articles" mode="prix" identifiant="cout" :avec-precision="false" />
        <div class="champ"><label for="notes">Notes (conditions, horaires, visite)</label><textarea id="notes" v-model="fiche.notes" rows="2" maxlength="2000" /></div>
        <div class="choix">
          <label><input v-model="fiche.est_interne" type="checkbox"> Notre blanchisserie</label>
          <label><input v-model="fiche.est_actif" type="checkbox"> Reçoit du linge</label>
        </div>
        <div class="boutons">
          <button type="submit" class="bouton">Enregistrer</button>
          <button type="button" class="bouton bouton-discret" @click="edite = null">Fermer</button>
        </div>
      </form>

      <p v-if="partenaires && !partenaires.length" class="aide">Aucun partenaire : ajoutez la première blanchisserie ou le premier pressing avec qui vous travaillez.</p>
      <div class="liste-cartes">
        <article v-for="p in partenaires ?? []" :key="p.id" class="carte partenaire" :class="{ inactif: !p.est_actif }">
          <header>
            <h2>{{ p.nom }}</h2>
            <span class="pastille" :class="{ 'pastille-attente': !p.est_actif }">{{ p.est_actif ? (p.est_interne ? 'Notre blanchisserie' : p.type === 'pressing' ? 'Pressing' : 'Blanchisserie') : 'Inactif' }}</span>
          </header>
          <p>{{ p.contact }} · <a :href="`tel:${p.telephone}`">{{ formaterTelephone(p.telephone) }}</a> · {{ p.quartier }}</p>
          <p class="aide">
            Délai {{ p.delai_jours }} j<template v-if="p.capacite_pieces_jour"> · {{ p.capacite_pieces_jour }} pièces/jour</template> ·
            {{ p.mode_tarif === 'kg' ? `${formaterFcfa(p.tarif_kg ?? 0)} le kilo` : `${Object.keys(p.tarifs).length} tarif(s) à la pièce` }} ·
            {{ p.hygiene_verifiee_le ? `hygiène vérifiée le ${formaterDate(p.hygiene_verifiee_le)}` : 'visite d\'hygiène à faire' }}
          </p>
          <button type="button" class="bouton bouton-discret" @click="editer(p)">Modifier</button>
        </article>
      </div>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.fiche { padding: 20px; margin-bottom: 16px; display: grid; gap: 8px; }
.fiche h2 { margin: 0; font-size: 1.2rem; }
.choix { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 6px 0; }
.choix label { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; min-height: 36px; }
.choix input { width: 20px; height: 20px; }
.prix-kg { max-width: 260px; }
.partenaire { padding: 14px 16px; display: grid; gap: 4px; justify-items: start; }
.partenaire header { display: flex; gap: 10px; align-items: center; justify-content: space-between; width: 100%; }
.partenaire h2 { margin: 0; font-size: 1.1rem; }
.partenaire p { margin: 0; }
.inactif { opacity: 0.75; }
</style>
