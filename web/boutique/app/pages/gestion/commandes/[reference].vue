<script setup lang="ts">
import type { CommandeGestion, Livreur, Paiement, Statut } from '~/types/commandes'
import type { ProduitGestion } from '~/types/gestion'
import { classeStatut } from '~/types/commandes'

const route = useRoute()
const reference = String(route.params.reference).toUpperCase()
useSeoMeta({ title: reference, robots: 'noindex' })
const { appeler, telecharger } = useApiBoutique()
const { verifie, autorise } = useEquipe()
const commande = ref<CommandeGestion | null>(null)
const erreur = ref('')
const envoi = ref(false)
const base = `/api/v1/admin/commandes/${reference}`

const MOYENS: Record<Paiement['moyen'], string> = {
  especes: 'Espèces', orange_money: 'Orange Money', moov_money: 'Moov Money', mobile_money: 'Paiement mobile', virement: 'Virement', cheque: 'Chèque',
}
// « Paiement mobile » : réservé aux paiements faits en ligne par le client.
const MOYENS_EQUIPE = Object.fromEntries(Object.entries(MOYENS).filter(([cle]) => cle !== 'mobile_money'))

// Confirmer une commande avec des articles faits à la demande la met en attente de l'acompte.
const acompteDemande = computed(() => {
  const c = commande.value
  return !!c && c.acompte_restant > 0 && ['en_attente', 'devis_envoye'].includes(c.statut)
})

function libelleAction(statut: Statut): string {
  const c = commande.value
  const confirmer = c?.statut === 'devis_envoye' ? 'Le client accepte le devis' : 'Confirmer la commande'
  const actions: Partial<Record<Statut, string>> = {
    confirmee: c?.statut === 'acompte_attendu' ? "Lancer sans attendre l'acompte" : confirmer,
    en_preparation: 'Mettre en préparation',
    prete: c?.statut === 'en_livraison' ? 'Livraison manquée : revient en boutique' : 'Marquer prête',
    en_livraison: 'Remettre au livreur',
    livree: c?.mode_livraison === 'retrait' ? 'Remise au client' : 'Marquer livrée',
    annulee: 'Annuler',
    devis_refuse: 'Le client refuse le devis',
  }
  return actions[statut] ?? statut
}

const passages = computed(() => (commande.value?.passages_possibles ?? []).filter(s =>
  s !== 'devis_envoye' && !(s === 'en_livraison' && commande.value?.mode_livraison === 'retrait')))
const etape = reactive({ note: '', visible_client: true, date_promise: '', livreur_id: '', garder_acompte: true })
// Annulation après un paiement : le client garde son droit au remboursement de ce qui dépasse
// l'acompte, et de tout si l'annulation vient de la boutique.
const retenue = computed(() => {
  const c = commande.value
  if (!c?.acompte || !c.montant_paye) return null
  const garde = Math.min(c.montant_paye, c.acompte)
  return { garde, rendre: c.montant_paye - garde, paye: c.montant_paye }
})
const livreurs = ref<Livreur[]>([])
const peutFacturer = computed(() => {
  const c = commande.value
  return !!c && !c.facture && !['devis_demande', 'devis_envoye', 'devis_refuse', 'annulee'].includes(c.statut)
})

const encaissement = reactive({ montant: 0, moyen: 'especes' as Paiement['moyen'], reference: '' })
const peutEncaisser = computed(() => {
  const c = commande.value
  return !!c && c.reste_a_payer > 0 && !['devis_demande', 'devis_envoye', 'devis_refuse', 'annulee'].includes(c.statut)
})

interface LigneEditee {
  produit_id: string | null
  variante_id: string | null
  libelle: string
  quantite: number
  prix_unitaire: number
  personnalisation: string | null
}
const devis = reactive({ lignes: [] as LigneEditee[], remise: 0, frais_livraison: 0, validite_jours: 30, note: '' })
const devisModifiable = computed(() => ['devis_demande', 'devis_envoye'].includes(commande.value?.statut ?? ''))
const totalDevis = computed(() =>
  devis.lignes.reduce((t, l) => t + l.quantite * l.prix_unitaire, 0) + devis.frais_livraison - devis.remise)

// Correction des articles au téléphone, avant la fabrication : taille, quantité, ajout,
// retrait. Une ligne déjà commandée garde son prix ; un ajout prend celui du catalogue.
interface LigneCorrigee {
  produit_id: string | null
  variante_id: string | null
  libelle: string
  quantite: number
  prix_unitaire: number | null
  personnalisation: string | null
}
const articles = reactive({ ouvert: false, lignes: [] as LigneCorrigee[], note: '', ajout: { produit_id: '', variante_id: '', quantite: 1 } })
const articlesModifiables = computed(() => ['en_attente', 'acompte_attendu'].includes(commande.value?.statut ?? ''))
const catalogue = ref<ProduitGestion[]>([])
// Articles vendables en ligne seulement : un article pharmaceutique passe par le pharmacien.
const ajoutables = computed(() => catalogue.value.filter(p => p.est_actif && p.categorie_reglementaire !== 'pharmaceutique'))
const variantesDe = computed(() => {
  const commandees = new Set(commande.value?.lignes.map(l => l.variante_id))
  return Object.fromEntries(catalogue.value.map(p => [p.id, p.variantes.filter(v => v.est_active || commandees.has(v.id))]))
})
async function ouvrirArticles() {
  const c = commande.value
  if (!c) return
  try {
    if (!catalogue.value.length) catalogue.value = await appeler<ProduitGestion[]>('/api/v1/admin/produits')
  } catch (e) {
    erreur.value = messageErreur(e)
    return
  }
  articles.lignes = c.lignes.map(l => ({
    produit_id: l.produit_id, variante_id: l.variante_id, libelle: l.libelle, quantite: l.quantite,
    prix_unitaire: l.prix_unitaire, personnalisation: l.personnalisation,
  }))
  articles.ouvert = true
}
// Même article, même variante qu'à la commande : le serveur garde le prix d'origine ; sinon
// prix du catalogue, au tarif de la commande (public ou professionnel).
function prixDOrigine(ligne: LigneCorrigee): number | null {
  const origine = commande.value?.lignes.find(l => l.produit_id === ligne.produit_id && l.variante_id === ligne.variante_id)
  return origine?.prix_unitaire ?? null
}
function ajouterArticle() {
  const { produit_id: id, variante_id: varianteId, quantite } = articles.ajout
  const variantes = (variantesDe.value[id] ?? []).filter(v => v.est_active)
  if (!id || (variantes.length > 0 && !varianteId)) return
  const variante = variantes.find(v => v.id === varianteId)
  const nom = catalogue.value.find(p => p.id === id)?.nom ?? ''
  articles.lignes.push({
    produit_id: id, variante_id: varianteId || null, libelle: variante ? `${nom} – ${variante.libelle}` : nom,
    quantite: Math.max(1, quantite), prix_unitaire: null, personnalisation: null,
  })
  Object.assign(articles.ajout, { produit_id: '', variante_id: '', quantite: 1 })
}
async function enregistrerArticles() {
  const ok = await executer('/articles', 'PUT', {
    lignes: articles.lignes.map(l => ({
      produit_id: l.produit_id, variante_id: l.variante_id, quantite: l.quantite,
      prix_unitaire: l.produit_id ? null : l.prix_unitaire, personnalisation: l.personnalisation,
      libelle: l.produit_id ? null : l.libelle,
    })),
    note: articles.note,
  })
  if (ok) {
    articles.ouvert = false
    articles.note = ''
  }
}

function preparer(c: CommandeGestion) {
  commande.value = c
  encaissement.montant = c.statut === 'acompte_attendu' ? c.acompte_restant : c.reste_a_payer
  etape.date_promise = c.date_promise ?? ''
  etape.garder_acompte = true
  devis.lignes = c.lignes.map(l => ({
    produit_id: l.produit_id, variante_id: l.variante_id, libelle: l.libelle,
    quantite: l.quantite, prix_unitaire: l.prix_unitaire, personnalisation: l.personnalisation,
  }))
  devis.remise = c.remise
  devis.frais_livraison = c.frais_livraison
}

async function executer(chemin: string, methode: 'POST' | 'PUT', corps: Record<string, unknown>) {
  envoi.value = true
  erreur.value = ''
  try {
    preparer(await appeler<CommandeGestion>(`${base}${chemin}`, { method: methode, body: corps }))
    return true
  } catch (e) {
    erreur.value = messageErreur(e)
    return false
  } finally {
    envoi.value = false
  }
}

async function avancer(statut: Statut) {
  if (statut === 'en_livraison' && !etape.livreur_id) {
    erreur.value = 'Choisissez le livreur.'
    return
  }
  const ok = await executer('/statut', 'POST', {
    statut, note: etape.note, visible_client: etape.visible_client, date_promise: etape.date_promise || null,
    livreur_id: statut === 'en_livraison' ? etape.livreur_id : null,
    garder_acompte: etape.garder_acompte,
  })
  if (ok) etape.note = ''
}

async function encaisser() {
  const ok = await executer('/paiements', 'POST', {
    montant: encaissement.montant, moyen: encaissement.moyen, reference: encaissement.reference || null,
  })
  if (ok) encaissement.reference = ''
}

async function envoyerDevis() {
  await executer('/devis', 'PUT', {
    lignes: devis.lignes.map(l => ({
      produit_id: l.produit_id, variante_id: l.variante_id, quantite: l.quantite, prix_unitaire: l.prix_unitaire,
      personnalisation: l.personnalisation, libelle: l.produit_id ? null : l.libelle,
    })),
    remise: devis.remise,
    frais_livraison: devis.frais_livraison,
    validite_jours: devis.validite_jours,
    note: devis.note,
  })
}

const lienWhatsapp = computed(() => {
  const c = commande.value
  if (!c) return ''
  const texte = `Bonjour ${c.nom_client}, ici Bibou, au sujet de votre ${c.est_devis ? 'demande de devis' : 'commande'} ${c.reference}.`
  return `https://wa.me/${c.telephone.replace('+', '')}?text=${encodeURIComponent(texte)}`
})

async function facturer() {
  await executer('/facture', 'POST', {})
}

watch(verifie, async () => {
  if (!autorise.value) return
  try {
    livreurs.value = (await appeler<Livreur[]>('/api/v1/admin/livreurs')).filter(l => l.est_actif)
    preparer(await appeler<CommandeGestion>(base))
  } catch (e) {
    erreur.value = messageErreur(e)
  }
})
</script>

<template>
  <section class="conteneur fiche-gestion">
    <AccesEquipe>
      <NuxtLink to="/gestion" class="retour">Toutes les commandes</NuxtLink>
      <div v-if="erreur" class="alerte alerte-erreur" role="alert">{{ erreur }}</div>
      <template v-if="commande">
        <div class="titre">
          <h1>{{ commande.reference }}</h1>
          <span :class="classeStatut(commande.statut)">{{ commande.statut_libelle }}</span>
        </div>
        <p class="aide">Reçue le {{ formaterDateHeure(commande.cree_le) }}<template v-if="commande.date_promise">, promise pour le {{ formaterDate(commande.date_promise) }}</template></p>

        <div class="colonnes">
          <div class="principal">
            <div class="carte bloc">
              <h2>Client</h2>
              <p class="contact">
                <strong>{{ commande.etablissement ?? commande.nom_client }}</strong>
                <span v-if="commande.etablissement">{{ commande.nom_client }}</span>
                <span v-if="commande.email">{{ commande.email }}</span>
              </p>
              <div class="actions">
                <a :href="`tel:${commande.telephone}`" class="bouton">Appeler le {{ formaterTelephone(commande.telephone) }}</a>
                <a :href="lienWhatsapp" target="_blank" rel="noopener" class="bouton bouton-secondaire">WhatsApp</a>
              </div>
              <p v-if="commande.note_client" class="note-client">« {{ commande.note_client }} »</p>
            </div>

            <div v-if="devisModifiable" class="carte bloc">
              <h2>{{ commande.statut === 'devis_envoye' ? 'Corriger le devis' : 'Établir le devis' }}</h2>
              <div class="table-devis">
                <div v-for="(l, i) in devis.lignes" :key="i" class="ligne-devis">
                  <input v-if="!l.produit_id" v-model="l.libelle" aria-label="Libellé" placeholder="Libellé de la ligne">
                  <span v-else>{{ l.libelle }}<small v-if="l.personnalisation">, texte « {{ l.personnalisation }} »</small></span>
                  <label>Qté <input v-model.number="l.quantite" type="number" min="1" inputmode="numeric"></label>
                  <label>Prix <input v-model.number="l.prix_unitaire" type="number" min="0" step="500" inputmode="numeric"></label>
                  <button type="button" class="bouton bouton-discret" @click="devis.lignes.splice(i, 1)">Retirer</button>
                </div>
              </div>
              <button type="button" class="bouton bouton-discret ajout" @click="devis.lignes.push({ produit_id: null, variante_id: null, libelle: '', quantite: 1, prix_unitaire: 0, personnalisation: null })">
                Ajouter une ligne libre (forfait broderie, transport…)
              </button>
              <div class="grille-devis">
                <div class="champ"><label for="remise">Remise (FCFA)</label><input id="remise" v-model.number="devis.remise" type="number" min="0" inputmode="numeric"></div>
                <div class="champ"><label for="frais">Livraison (FCFA)</label><input id="frais" v-model.number="devis.frais_livraison" type="number" min="0" inputmode="numeric"></div>
                <div class="champ"><label for="validite">Validité (jours)</label><input id="validite" v-model.number="devis.validite_jours" type="number" min="1" max="120" inputmode="numeric"></div>
              </div>
              <div class="champ"><label for="note-devis">Message au client (facultatif)</label><input id="note-devis" v-model="devis.note" maxlength="500"></div>
              <p class="total-devis">Total du devis : <strong>{{ formaterFcfa(totalDevis) }}</strong></p>
              <button type="button" class="bouton" :disabled="envoi || !devis.lignes.length" @click="envoyerDevis">Envoyer le devis</button>
            </div>

            <div class="carte bloc carte-articles">
              <h2>
                Articles
                <span v-if="commande.tarif_professionnel" class="pastille pastille-accent">Tarif professionnel</span>
              </h2>
              <template v-if="articles.ouvert">
                <div class="table-devis">
                  <div v-for="(l, i) in articles.lignes" :key="i" class="ligne-devis ligne-article">
                    <input v-if="!l.produit_id" v-model="l.libelle" aria-label="Libellé" placeholder="Libellé de la ligne">
                    <span v-else>{{ l.libelle.split(' – ')[0] }}<small v-if="l.personnalisation">, texte « {{ l.personnalisation }} »</small></span>
                    <label v-if="l.produit_id && variantesDe[l.produit_id]?.length">
                      Variante
                      <select v-model="l.variante_id">
                        <option v-for="v in variantesDe[l.produit_id]" :key="v.id" :value="v.id">{{ v.libelle }}{{ v.est_active ? '' : ' (retirée)' }}</option>
                      </select>
                    </label>
                    <label>Qté <input v-model.number="l.quantite" type="number" min="1" inputmode="numeric"></label>
                    <label v-if="!l.produit_id">Prix <input v-model.number="l.prix_unitaire" type="number" min="0" step="500" inputmode="numeric"></label>
                    <span v-else class="aide">{{ prixDOrigine(l) !== null ? formaterFcfa(prixDOrigine(l)!) : 'prix du catalogue' }}</span>
                    <button type="button" class="bouton bouton-discret" :aria-label="`Retirer ${l.libelle}`" @click="articles.lignes.splice(i, 1)">Retirer</button>
                  </div>
                </div>
                <fieldset class="ajout-article">
                  <legend>Ajouter un article du catalogue</legend>
                  <select v-model="articles.ajout.produit_id" aria-label="Article à ajouter" @change="articles.ajout.variante_id = ''">
                    <option value="">Choisir un article…</option>
                    <option v-for="p in ajoutables" :key="p.id" :value="p.id">{{ p.nom }}</option>
                  </select>
                  <select v-if="articles.ajout.produit_id && variantesDe[articles.ajout.produit_id]?.length" v-model="articles.ajout.variante_id" aria-label="Variante de l'article à ajouter">
                    <option value="">Variante…</option>
                    <option v-for="v in variantesDe[articles.ajout.produit_id]?.filter(v => v.est_active)" :key="v.id" :value="v.id">{{ v.libelle }}</option>
                  </select>
                  <input v-model.number="articles.ajout.quantite" type="number" min="1" inputmode="numeric" aria-label="Quantité à ajouter">
                  <button type="button" class="bouton bouton-secondaire" @click="ajouterArticle">Ajouter</button>
                </fieldset>
                <button type="button" class="bouton bouton-discret ajout" @click="articles.lignes.push({ produit_id: null, variante_id: null, libelle: '', quantite: 1, prix_unitaire: 0, personnalisation: null })">
                  Ajouter une ligne libre (retouche, transport…)
                </button>
                <div class="champ"><label for="note-articles">Note visible du client (facultatif)</label><input id="note-articles" v-model="articles.note" maxlength="500" placeholder="Taille L au lieu de M, à votre demande"></div>
                <div class="actions-articles">
                  <button type="button" class="bouton" :disabled="envoi || !articles.lignes.length" @click="enregistrerArticles">Enregistrer les corrections</button>
                  <button type="button" class="bouton bouton-discret" @click="articles.ouvert = false">Abandonner</button>
                </div>
              </template>
              <template v-else>
                <DetailCommande :commande="commande" />
                <div v-if="articlesModifiables" class="corriger">
                  <button type="button" class="bouton bouton-secondaire" @click="ouvrirArticles">Corriger les articles</button>
                  <span class="aide">Taille, quantité, ajout ou retrait, avant la fabrication. Total, acompte et code promo suivent.</span>
                </div>
                <button v-if="commande.devis_emis_le" type="button" class="bouton bouton-secondaire" @click="telecharger(`${base}/devis.pdf`, `devis-${commande.reference}.pdf`)">
                  Télécharger le devis (PDF)
                </button>
              </template>
            </div>
          </div>

          <aside class="lateral">
            <div v-if="passages.length" class="carte bloc">
              <h2>Étape suivante</h2>
              <div class="champ">
                <label for="note-etape">Note (facultatif)</label>
                <input id="note-etape" v-model="etape.note" maxlength="500" placeholder="Livreur : Ibrahim, 14 h">
              </div>
              <label class="case"><input v-model="etape.visible_client" type="checkbox"> Visible par le client</label>
              <div v-if="passages.includes('en_livraison')" class="champ">
                <label for="livreur">Livreur</label>
                <select id="livreur" v-model="etape.livreur_id">
                  <option value="" disabled>Choisir…</option>
                  <option v-for="l in livreurs" :key="l.id" :value="l.id">{{ l.nom }}</option>
                </select>
                <span v-if="!livreurs.length" class="aide">Ajoutez d'abord un livreur dans Livraisons.</span>
              </div>
              <p v-if="acompteDemande" class="aide">
                Articles faits à la demande : la commande attendra l'acompte de {{ formaterFcfa(commande.acompte_restant) }}
                (SMS au client). La date est fixée à sa réception.
              </p>
              <div v-else-if="passages.includes('confirmee')" class="champ">
                <label for="date-promise">Date promise</label>
                <input id="date-promise" v-model="etape.date_promise" type="date">
              </div>
              <fieldset v-if="passages.includes('annulee') && retenue" class="retenue">
                <legend>En cas d'annulation</legend>
                <label class="case">
                  <input v-model="etape.garder_acompte" type="radio" name="retenue" :value="true">
                  <span>
                    À la demande du client : l'acompte de {{ formaterFcfa(retenue.garde) }} est gardé<template v-if="retenue.rendre">,
                      {{ formaterFcfa(retenue.rendre) }} à lui rendre</template>
                  </span>
                </label>
                <label class="case">
                  <input v-model="etape.garder_acompte" type="radio" name="retenue" :value="false">
                  <span>Par la boutique : tout lui rendre ({{ formaterFcfa(retenue.paye) }})</span>
                </label>
              </fieldset>
              <div class="actions">
                <button
                  v-for="s in passages" :key="s" type="button" :disabled="envoi"
                  :class="s === 'annulee' || s === 'devis_refuse' ? 'bouton bouton-secondaire' : 'bouton'"
                  @click="avancer(s)"
                >{{ libelleAction(s) }}</button>
              </div>
            </div>

            <div class="carte bloc">
              <h2>Paiement</h2>
              <p>Payé : <strong>{{ formaterFcfa(commande.montant_paye) }}</strong> sur {{ formaterFcfa(commande.total) }}</p>
              <p v-if="commande.acompte" class="aide">
                Acompte (non remboursable) : {{ formaterFcfa(commande.acompte) }}<template v-if="commande.statut === 'acompte_attendu'">,
                  reste {{ formaterFcfa(commande.acompte_restant) }} à recevoir pour lancer la fabrication</template><template
                  v-else-if="commande.acompte_garde">, {{ formaterFcfa(commande.acompte_garde) }} gardé à l'annulation</template>.
              </p>
              <ul v-if="commande.paiements.length" class="paiements">
                <li v-for="p in commande.paiements" :key="p.id">
                  {{ formaterFcfa(p.montant) }}, {{ MOYENS[p.moyen] }}<span v-if="!p.encaisse_par">, payé en ligne</span><span v-if="p.reference"> ({{ p.reference }})</span>
                  <small>{{ formaterDateHeure(p.encaisse_le) }}</small>
                </li>
              </ul>
              <p v-if="commande.facture" class="facture">
                Facture {{ commande.facture }}
                <button type="button" class="bouton bouton-discret" @click="telecharger(`${base}/facture.pdf`, `facture-${commande.facture}.pdf`)">Télécharger</button>
              </p>
              <button v-else-if="peutFacturer" type="button" class="bouton bouton-secondaire" :disabled="envoi" @click="facturer">Émettre la facture</button>
              <form v-if="peutEncaisser" class="encaissement" @submit.prevent="encaisser">
                <div class="champ"><label for="montant">Montant (FCFA)</label><input id="montant" v-model.number="encaissement.montant" type="number" min="1" :max="commande.reste_a_payer" inputmode="numeric" required></div>
                <div class="champ">
                  <label for="moyen">Moyen</label>
                  <select id="moyen" v-model="encaissement.moyen">
                    <option v-for="(nom, cle) in MOYENS_EQUIPE" :key="cle" :value="cle">{{ nom }}</option>
                  </select>
                </div>
                <div class="champ"><label for="ref-paiement">N° de transaction (facultatif)</label><input id="ref-paiement" v-model="encaissement.reference" maxlength="80"></div>
                <button type="submit" class="bouton bouton-large" :disabled="envoi">Enregistrer l'encaissement</button>
              </form>
            </div>

            <div class="carte bloc">
              <h2>Historique</h2>
              <HistoriqueCommande :evenements="commande.historique_complet" />
            </div>
          </aside>
        </div>
      </template>
    </AccesEquipe>
  </section>
</template>

<style scoped>
.fiche-gestion { padding-top: 20px; }
.retour { display: inline-block; margin-bottom: 12px; }
.titre { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.titre h1 { margin: 0; }
.colonnes { display: grid; gap: 20px; margin-top: 16px; }
@media (min-width: 960px) { .colonnes { grid-template-columns: minmax(0, 1fr) 380px; align-items: start; } }
.principal, .lateral { display: grid; gap: 16px; align-content: start; }
.bloc { padding: 18px; display: grid; gap: 10px; }
.bloc h2 { margin: 0; font-size: 1.1rem; }
.bloc p { margin: 0; }
.contact { display: grid; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }
.note-client { padding: 10px 12px; border-radius: 10px; background: var(--fond-doux); }
.case { display: flex; align-items: center; gap: 8px; }
.case input { flex: none; width: 20px; height: 20px; accent-color: var(--primaire); }
.retenue { border: 1px solid var(--bordure); border-radius: 10px; padding: 8px 12px 12px; display: grid; gap: 8px; }
.retenue legend { font-weight: 650; padding: 0 4px; }
.retenue .case { align-items: flex-start; }
.table-devis { display: grid; gap: 8px; }
.ajout-article { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; border: 1px dashed var(--bordure); border-radius: 10px; padding: 8px 10px 10px; margin: 4px 0; }
.ajout-article legend { font-weight: 650; padding: 0 4px; }
.ajout-article select, .ajout-article input { min-height: 40px; border: 1.5px solid var(--bordure); border-radius: 8px; padding: 0 8px; font: inherit; }
/* Largeur en pourcentage : un long nom d'article ne fait plus déborder la page sur téléphone. */
.ajout-article select { flex: 1 1 14em; width: 100%; min-width: 0; }
.ajout-article input { width: 72px; }
.actions-articles { display: flex; flex-wrap: wrap; gap: 8px; }
/* Après .ligne-devis (grille du devis) : ici, les champs passent à la ligne sur téléphone. */
.ligne-devis.ligne-article { display: flex; flex-wrap: wrap; }
.ligne-devis.ligne-article > :first-child { flex: 1 1 100%; }
.ligne-devis select { min-height: 40px; max-width: 100%; padding: 0 0.5em; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; }
.carte-articles h2 { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.corriger { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-top: 8px; }
.ligne-devis {
  display: grid; grid-template-columns: 1fr auto auto; gap: 6px 10px; align-items: center;
  padding: 10px; border: 1px solid var(--bordure); border-radius: 10px;
}
.ligne-devis > :first-child { grid-column: 1 / -1; font-weight: 600; }
.ligne-devis input { min-height: 40px; width: 100%; padding: 0 0.6em; border: 1.5px solid var(--bordure); border-radius: 8px; font: inherit; }
.ligne-devis label { display: flex; align-items: center; gap: 6px; font-size: 0.9rem; }
.ligne-devis label input { width: 96px; }
.ligne-devis small { color: var(--texte-doux); font-weight: 400; }
.ajout { justify-self: start; }
.grille-devis { display: grid; gap: 0 12px; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
.grille-devis .champ { min-width: 0; }
.grille-devis input { width: 100%; min-width: 0; }
.total-devis { font-size: 1.1rem; }
.paiements { margin: 0; padding-left: 1.1em; }
.paiements small { display: block; color: var(--texte-doux); }
.encaissement .champ { margin-bottom: 0.6rem; }
.facture { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-weight: 650; }
</style>
