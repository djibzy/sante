<script setup lang="ts">
import type { ProduitGestion, RayonGestion, VarianteGestion } from '~/types/gestion'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id))
const nouveau = computed(() => id.value === 'nouveau')
useSeoMeta({ title: () => (nouveau.value ? 'Nouveau produit' : 'Modifier un produit'), robots: 'noindex' })
const { appeler } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const METIERS: Record<string, string> = {
  infirmier: 'Infirmiers', 'sage-femme': 'Sages-femmes', medecin: 'Médecins', pharmacie: 'Pharmacie',
  laboratoire: 'Laboratoire', dentiste: 'Dentistes', 'aide-soignant': 'Aides-soignants', etudiant: 'Étudiants',
}
const rayons = ref<RayonGestion[]>([])
const produit = ref<ProduitGestion | null>(null)
const erreur = ref('')
const message = ref('')
const envoi = ref(false)

const vide = () => ({
  slug: '', nom: '', resume: '', description: '', rayon_slug: '', categorie_reglementaire: 'libre' as 'libre' | 'pharmaceutique',
  personnalisable: false, prix_public: null as number | null, prix_pro: null as number | null, prix_avant_promo: null as number | null,
  delai_jours: 7, poste_atelier: '' as string, seuil_alerte: 0, metiers: [] as string[], genre: '' as string, manches: '' as string,
  collection: '', matiere: '', entretien: '', est_nouveau: false, est_actif: true,
})
const fiche = reactive(vide())
const nouvelleCouleur = reactive({ couleur: '', hex: '#1f4fa8', tailles: 'XS, S, M, L, XL, XXL', prix: null as number | null })
const photos = ref<{ url: string; texte_alternatif: string; couleur: string | null }[]>([])
const adresse = useAdresseImage()
const envoiPhoto = reactive({ fichier: null as File | null, texte: '', couleur: '' })
// Couleur de l'article sur la photo : la fiche montre la bonne photo quand le client choisit
// une couleur, et la page « Explorer » l'utilise pour cette couleur.
const couleursDuProduit = computed(() => [...new Set((produit.value?.variantes ?? []).map(v => v.couleur).filter((c): c is string => !!c))])

async function envoyerPhoto() {
  if (!envoiPhoto.fichier) return
  const donnees = new FormData()
  donnees.append('fichier', envoiPhoto.fichier)
  donnees.append('texte_alternatif', envoiPhoto.texte || fiche.nom)
  if (envoiPhoto.couleur) donnees.append('couleur', envoiPhoto.couleur)
  const resultat = await executer(() => appeler<ProduitGestion>(`/api/v1/admin/produits/${id.value}/photos`, { method: 'POST', body: donnees }), 'Photo ajoutée.')
  if (resultat) {
    remplir(resultat)
    envoiPhoto.fichier = null
    envoiPhoto.texte = ''
    envoiPhoto.couleur = ''
  }
}

function remplir(p: ProduitGestion) {
  produit.value = p
  Object.assign(fiche, {
    ...p, poste_atelier: p.poste_atelier ?? '', genre: p.genre ?? '', manches: p.manches ?? '', collection: p.collection ?? '',
  })
  photos.value = p.images.map(i => ({ ...i, couleur: i.couleur ?? null }))
}

function corps() {
  const commun = {
    nom: fiche.nom, resume: fiche.resume, description: fiche.description, personnalisable: fiche.personnalisable,
    prix_public: fiche.categorie_reglementaire === 'pharmaceutique' ? null : fiche.prix_public,
    prix_pro: fiche.categorie_reglementaire === 'pharmaceutique' ? null : fiche.prix_pro,
    prix_avant_promo: fiche.prix_avant_promo || null, delai_jours: fiche.delai_jours,
    poste_atelier: fiche.poste_atelier || null, seuil_alerte: fiche.seuil_alerte, metiers: fiche.metiers,
    genre: fiche.genre || null, manches: fiche.manches || null, collection: fiche.collection.trim() || null,
    matiere: fiche.matiere, entretien: fiche.entretien, est_nouveau: fiche.est_nouveau,
  }
  return nouveau.value
    ? { ...commun, slug: fiche.slug, rayon_slug: fiche.rayon_slug, categorie_reglementaire: fiche.categorie_reglementaire }
    : { ...commun, est_actif: fiche.est_actif }
}

async function executer<T>(action: () => Promise<T>, succes: string): Promise<T | null> {
  envoi.value = true
  erreur.value = ''
  message.value = ''
  try {
    const resultat = await action()
    message.value = succes
    return resultat
  } catch (e) {
    erreur.value = messageErreur(e)
    return null
  } finally {
    envoi.value = false
  }
}

async function recharger() {
  remplir(await appeler<ProduitGestion>(`/api/v1/admin/produits/${id.value}`))
}

async function enregistrer() {
  if (nouveau.value) {
    const cree = await executer(() => appeler<{ id: string }>('/api/v1/admin/produits', { method: 'POST', body: corps() }), 'Produit créé.')
    if (cree) await router.replace(`/gestion/catalogue/${cree.id}`)
    return
  }
  const ok = await executer(() => appeler(`/api/v1/admin/produits/${id.value}`, { method: 'PATCH', body: corps() }), 'Modifications enregistrées.')
  if (ok !== null) await recharger()
}

function code(texte: string) {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, '')
}

async function ajouterCouleur() {
  const p = produit.value
  if (!p) return
  const tailles = nouvelleCouleur.tailles.split(',').map(t => t.trim()).filter(Boolean)
  const couleur = nouvelleCouleur.couleur.trim()
  const lignes = (tailles.length ? tailles : [null]).map(taille => ({
    sku: [p.slug, couleur && code(couleur), taille].filter(Boolean).join('-').toUpperCase(),
    libelle: [taille && `${p.rayon_slug === 'chaussures' ? 'Pointure' : 'Taille'} ${taille}`, couleur].filter(Boolean).join(' · '),
    taille, couleur: couleur || null, couleur_hex: couleur ? nouvelleCouleur.hex : null, prix: nouvelleCouleur.prix || null,
    position: p.variantes.length,
  }))
  const ok = await executer(async () => {
    for (const ligne of lignes) await appeler(`/api/v1/admin/produits/${p.id}/variantes`, { method: 'POST', body: ligne })
    return true
  }, `${lignes.length} variante${lignes.length > 1 ? 's' : ''} ajoutée${lignes.length > 1 ? 's' : ''}.`)
  await recharger()
  if (ok) nouvelleCouleur.couleur = ''
}

async function modifierVariante(v: VarianteGestion, changements: Partial<VarianteGestion>) {
  await executer(() => appeler(`/api/v1/admin/variantes/${v.id}`, { method: 'PATCH', body: changements }), 'Variante enregistrée.')
  await recharger()
}

async function enregistrerPhotos() {
  const ok = await executer(() => appeler(`/api/v1/admin/produits/${id.value}/images`, {
    method: 'PUT', body: { images: photos.value.filter(i => i.url.trim()) },
  }), 'Photos enregistrées.')
  if (ok !== null) await recharger()
}

watch(verifie, async () => {
  if (!autorise.value) return
  try {
    rayons.value = await appeler<RayonGestion[]>('/api/v1/admin/rayons')
    if (!nouveau.value) await recharger()
    else fiche.rayon_slug = rayons.value[0]?.slug ?? ''
  } catch (e) {
    erreur.value = messageErreur(e)
  }
})
</script>

<template>
  <section class="conteneur edition">
    <AccesEquipe>
      <NuxtLink to="/gestion/catalogue" class="retour">Tout le catalogue</NuxtLink>
      <div class="titre">
        <h1>{{ nouveau ? 'Nouveau produit' : fiche.nom }}</h1>
        <NuxtLink v-if="produit && produit.est_actif" :to="`/produits/${produit.slug}`" target="_blank">Voir en boutique</NuxtLink>
      </div>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <div v-if="message" class="alerte alerte-succes" role="status">{{ message }}</div>

      <form class="carte bloc" @submit.prevent="enregistrer">
        <h2>Fiche</h2>
        <div class="grille">
          <div class="champ"><label for="nom">Nom</label><input id="nom" v-model="fiche.nom" required minlength="2" maxlength="200"></div>
          <div v-if="nouveau" class="champ">
            <label for="slug">Adresse (slug)</label>
            <input id="slug" v-model="fiche.slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="blouse-femme-cintree">
            <span class="aide">Minuscules, chiffres et tirets ; ne change plus ensuite.</span>
          </div>
          <div class="champ">
            <label for="rayon">Rayon</label>
            <select id="rayon" v-model="fiche.rayon_slug" :disabled="!nouveau">
              <option v-for="r in rayons" :key="r.slug" :value="r.slug">{{ r.nom }}</option>
            </select>
          </div>
          <div class="champ">
            <label for="categorie">Catégorie réglementaire</label>
            <select id="categorie" v-model="fiche.categorie_reglementaire" :disabled="!nouveau">
              <option value="libre">Vente libre</option>
              <option value="pharmaceutique">Pharmaceutique (pharmacien partenaire, sans prix)</option>
            </select>
          </div>
        </div>
        <div class="champ"><label for="resume">Résumé (une phrase)</label><input id="resume" v-model="fiche.resume" maxlength="300"></div>
        <div class="champ"><label for="description">Description</label><textarea id="description" v-model="fiche.description" rows="3" /></div>

        <template v-if="fiche.categorie_reglementaire === 'libre'">
          <h3>Prix et délais</h3>
          <div class="grille">
            <div class="champ"><label for="prix">Prix public (FCFA)</label><input id="prix" v-model.number="fiche.prix_public" type="number" min="0" step="500" required></div>
            <div class="champ"><label for="prix-pro">Prix professionnel</label><input id="prix-pro" v-model.number="fiche.prix_pro" type="number" min="0" step="500"></div>
            <div class="champ"><label for="prix-barre">Prix barré (promotion)</label><input id="prix-barre" v-model.number="fiche.prix_avant_promo" type="number" min="0" step="500"><span class="aide">Vide : pas de promotion.</span></div>
            <div class="champ"><label for="delai">Délai (jours)</label><input id="delai" v-model.number="fiche.delai_jours" type="number" min="0" max="120"></div>
            <div class="champ">
              <label for="poste">Poste de l'atelier</label>
              <select id="poste" v-model="fiche.poste_atelier">
                <option value="">Aucun : vendu tel quel, suivi en stock</option>
                <option value="broderie">Broderie</option>
                <option value="impression">Impression</option>
                <option value="assemblage">Assemblage des kits</option>
              </select>
            </div>
            <div class="champ"><label for="seuil">Seuil d'alerte du stock</label><input id="seuil" v-model.number="fiche.seuil_alerte" type="number" min="0"></div>
          </div>
        </template>

        <h3>Pour qui</h3>
        <fieldset class="cases">
          <legend class="visuellement-cache">Métiers</legend>
          <label v-for="(nom, cle) in METIERS" :key="cle"><input v-model="fiche.metiers" type="checkbox" :value="cle"> {{ nom }}</label>
        </fieldset>
        <div class="grille">
          <div class="champ">
            <label for="genre">Genre</label>
            <select id="genre" v-model="fiche.genre"><option value="">Non précisé</option><option value="femme">Femme</option><option value="homme">Homme</option><option value="mixte">Mixte</option></select>
          </div>
          <div class="champ">
            <label for="manches">Manches</label>
            <select id="manches" v-model="fiche.manches"><option value="">Sans objet</option><option value="courtes">Courtes</option><option value="longues">Longues</option></select>
          </div>
          <div class="champ"><label for="collection">Collection</label><input id="collection" v-model="fiche.collection" maxlength="60" placeholder="Essentielle, Wax…"></div>
        </div>
        <div class="grille">
          <div class="champ"><label for="matiere">Matière</label><input id="matiere" v-model="fiche.matiere" maxlength="200"></div>
          <div class="champ"><label for="entretien">Entretien</label><input id="entretien" v-model="fiche.entretien" maxlength="300"></div>
        </div>
        <div class="cases">
          <label><input v-model="fiche.personnalisable" type="checkbox"> Personnalisable (broderie du nom)</label>
          <label><input v-model="fiche.est_nouveau" type="checkbox"> Nouveauté</label>
          <label v-if="!nouveau"><input v-model="fiche.est_actif" type="checkbox"> En ligne</label>
        </div>
        <button type="submit" class="bouton" :disabled="envoi">{{ nouveau ? 'Créer le produit' : 'Enregistrer' }}</button>
      </form>

      <div v-if="produit" class="carte bloc">
        <h2>Couleurs et tailles</h2>
        <table v-if="produit.variantes.length" class="variantes">
          <thead><tr><th scope="col">Variante</th><th scope="col">Code</th><th scope="col">Prix propre</th><th scope="col" /></tr></thead>
          <tbody>
            <tr v-for="v in produit.variantes" :key="v.id" :class="{ inactive: !v.est_active }">
              <td><span v-if="v.couleur_hex" class="teinte" :style="{ background: v.couleur_hex }" />{{ v.libelle }}</td>
              <td><small>{{ v.sku }}</small></td>
              <td><input :value="v.prix ?? ''" type="number" min="0" step="500" :aria-label="`Prix de ${v.libelle}`" placeholder="Prix du produit" @change="modifierVariante(v, { prix: Number(($event.target as HTMLInputElement).value) || null })"></td>
              <td><button type="button" class="bouton bouton-discret" @click="modifierVariante(v, { est_active: !v.est_active })">{{ v.est_active ? 'Retirer' : 'Remettre' }}</button></td>
            </tr>
          </tbody>
        </table>
        <form class="ajout-couleur" @submit.prevent="ajouterCouleur">
          <div class="champ"><label for="couleur">Couleur</label><input id="couleur" v-model="nouvelleCouleur.couleur" maxlength="40" placeholder="Bleu roi (vide si sans couleur)"></div>
          <div class="champ"><label for="hex">Pastille</label><input id="hex" v-model="nouvelleCouleur.hex" type="color"></div>
          <div class="champ"><label for="tailles">Tailles, séparées par des virgules</label><input id="tailles" v-model="nouvelleCouleur.tailles"></div>
          <div class="champ"><label for="prix-variante">Prix propre (facultatif)</label><input id="prix-variante" v-model.number="nouvelleCouleur.prix" type="number" min="0" step="500"></div>
          <button type="submit" class="bouton bouton-secondaire" :disabled="envoi">Ajouter ces variantes</button>
        </form>
      </div>

      <div v-if="produit" class="carte bloc">
        <h2>Photos</h2>
        <form class="envoi-photo" @submit.prevent="envoyerPhoto">
          <div class="champ">
            <label for="fichier-photo">Photo (prise au téléphone ou sur l'ordinateur)</label>
            <input id="fichier-photo" type="file" accept="image/jpeg,image/png,image/webp" required @change="envoiPhoto.fichier = ($event.target as HTMLInputElement).files?.[0] ?? null">
          </div>
          <div class="champ">
            <label for="texte-photo">Ce qu'on voit sur la photo</label>
            <input id="texte-photo" v-model="envoiPhoto.texte" maxlength="200" placeholder="Tunique bleu roi, de face">
          </div>
          <div v-if="couleursDuProduit.length" class="champ">
            <label for="couleur-photo">Couleur de l'article sur la photo</label>
            <select id="couleur-photo" v-model="envoiPhoto.couleur">
              <option value="">Toutes / non précisée</option>
              <option v-for="c in couleursDuProduit" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <button type="submit" class="bouton" :disabled="envoi || !envoiPhoto.fichier">Envoyer la photo</button>
        </form>
        <p class="aide">La photo est réduite et nettoyée de ses informations (position, téléphone). Vous pouvez aussi indiquer l'adresse d'une photo déjà en ligne.</p>
        <div v-for="(photo, i) in photos" :key="i" class="photo">
          <img v-if="photo.url" :src="adresse(photo.url)" alt="" width="56" height="70">
          <input v-model="photo.url" :aria-label="`Adresse de la photo ${i + 1}`" placeholder="https://…">
          <input v-model="photo.texte_alternatif" :aria-label="`Description de la photo ${i + 1}`" placeholder="Blouse blanche, de face">
          <select v-if="couleursDuProduit.length" v-model="photo.couleur" :aria-label="`Couleur de l'article sur la photo ${i + 1}`">
            <option :value="null">Toutes couleurs</option>
            <option v-for="c in couleursDuProduit" :key="c" :value="c">{{ c }}</option>
          </select>
          <button type="button" class="bouton bouton-discret" @click="photos.splice(i, 1)">Retirer</button>
        </div>
        <div class="actions">
          <button type="button" class="bouton bouton-secondaire" @click="photos.push({ url: '', texte_alternatif: '', couleur: null })">Ajouter une photo</button>
          <button type="button" class="bouton" :disabled="envoi" @click="enregistrerPhotos">Enregistrer les photos</button>
        </div>
      </div>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.edition { padding-top: 20px; display: grid; gap: 16px; }
.retour { justify-self: start; }
.titre { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 12px; }
.titre h1 { margin: 0; }
.bloc { padding: 20px; display: grid; gap: 6px; }
.bloc h2 { margin: 0 0 8px; font-size: 1.2rem; }
.bloc h3 { margin: 12px 0 4px; font-size: 1rem; }
.grille { display: grid; gap: 0 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); }
.grille .champ { min-width: 0; }
.cases { border: 0; padding: 0; margin: 4px 0 12px; display: flex; flex-wrap: wrap; gap: 10px 18px; }
.cases input { width: 18px; height: 18px; accent-color: var(--primaire); vertical-align: -3px; }
.bloc > .bouton { justify-self: start; }
.variantes { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.variantes th, .variantes td { padding: 8px; text-align: left; border-bottom: 1px solid var(--bordure); }
.variantes thead th { font-size: 0.85rem; color: var(--texte-doux); }
.variantes input { width: 130px; min-height: 38px; padding: 0 8px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; }
.variantes tr.inactive td { color: var(--texte-doux); text-decoration: line-through; }
.teinte { display: inline-block; width: 14px; height: 14px; border-radius: 50%; margin-right: 8px; vertical-align: -2px; box-shadow: inset 0 0 0 1px rgba(23, 21, 58, 0.25); }
.ajout-couleur { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 170px), 1fr)); align-items: end; }
.ajout-couleur input[type='color'] { padding: 4px; width: 64px; }
.ajout-couleur .bouton { margin-bottom: 1rem; }
.photo { display: grid; grid-template-columns: 56px minmax(0, 2fr) minmax(0, 2fr) minmax(0, 1fr) auto; gap: 8px; align-items: center; }
.photo select { min-height: 40px; padding: 0 6px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; min-width: 0; }
@media (max-width: 640px) { .photo { grid-template-columns: 56px minmax(0, 1fr); } .photo > :not(img) { grid-column: 2; } }
.photo img { object-fit: cover; border-radius: 6px; background: var(--fond-doux); }
.photo input { min-height: 40px; padding: 0 8px; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; min-width: 0; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.envoi-photo { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); align-items: end; }
.envoi-photo .bouton { margin-bottom: 1rem; }
.envoi-photo input[type='file'] { padding: 8px; }
</style>
