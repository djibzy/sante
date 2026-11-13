/**
 * Panier gardé sur l'appareil (localStorage) : il survit aux coupures de réseau et aux
 * rechargements. Les prix affichés ici sont indicatifs ; le serveur recalcule tout.
 */
export interface LignePanier {
  produit_id: string
  variante_id: string | null
  quantite: number
  personnalisation: string | null
  slug: string
  nom: string
  variante: string | null
  rayon_slug: string
  prix_indicatif: number | null
}

export interface ChoixLivraison {
  mode: 'retrait' | 'livraison'
  zone_id: string | null
  adresse: string
}

const CLE_PANIER = 'bibou-panier'
const CLE_SUIVIS = 'bibou-suivis'
const CLE_CODE = 'bibou-code-promo'
const QUANTITE_MAX = 500

export interface SuiviLocal {
  reference: string
  cle: string
  cree_le: string
  est_devis: boolean
}

function lire<T>(cle: string, defaut: T): T {
  try {
    const brut = localStorage.getItem(cle)
    return brut ? (JSON.parse(brut) as T) : defaut
  } catch {
    return defaut
  }
}

function ecrire(cle: string, valeur: unknown) {
  try {
    localStorage.setItem(cle, JSON.stringify(valeur))
  } catch {
    // Navigation privée ou stockage plein : le panier reste en mémoire pour cette visite.
  }
}

export function usePanier() {
  const lignes = useState<LignePanier[]>('panier', () => [])
  const livraison = useState<ChoixLivraison>('livraison', () => ({ mode: 'retrait', zone_id: null, adresse: '' }))
  const suivis = useState<SuiviLocal[]>('suivis', () => [])
  // Code de réduction saisi au panier ; le serveur le vérifie au chiffrage puis à la commande.
  const codePromo = useState<string>('code-promo', () => '')
  const nombre = computed(() => lignes.value.reduce((total, l) => total + l.quantite, 0))

  function restaurer() {
    lignes.value = lire<LignePanier[]>(CLE_PANIER, [])
    suivis.value = lire<SuiviLocal[]>(CLE_SUIVIS, [])
    codePromo.value = lire<string>(CLE_CODE, '')
  }

  function choisirCode(code: string) {
    codePromo.value = code.trim().toUpperCase().slice(0, 30)
    ecrire(CLE_CODE, codePromo.value)
  }

  function enregistrer() {
    ecrire(CLE_PANIER, lignes.value)
  }

  function ajouter(ligne: LignePanier) {
    const meme = lignes.value.find(l =>
      l.produit_id === ligne.produit_id
      && l.variante_id === ligne.variante_id
      && (l.personnalisation ?? '') === (ligne.personnalisation ?? ''))
    if (meme) meme.quantite = Math.min(meme.quantite + ligne.quantite, QUANTITE_MAX)
    else lignes.value.push({ ...ligne, quantite: Math.min(ligne.quantite, QUANTITE_MAX) })
    enregistrer()
  }

  function changerQuantite(index: number, quantite: number) {
    const ligne = lignes.value[index]
    if (!ligne) return
    if (quantite <= 0) lignes.value.splice(index, 1)
    else ligne.quantite = Math.min(quantite, QUANTITE_MAX)
    enregistrer()
  }

  function vider() {
    lignes.value = []
    enregistrer()
    choisirCode('') // le code accompagnait ce panier-là
  }

  function retenirSuivi(suivi: SuiviLocal) {
    suivis.value = [suivi, ...suivis.value.filter(s => s.reference !== suivi.reference)].slice(0, 20)
    ecrire(CLE_SUIVIS, suivis.value)
  }

  /** Ce que l'API attend : identifiants et quantités, jamais de prix. */
  const demande = computed(() => lignes.value.map(l => ({
    produit_id: l.produit_id,
    variante_id: l.variante_id,
    quantite: l.quantite,
    personnalisation: l.personnalisation,
  })))

  return {
    lignes, livraison, suivis, nombre, demande, codePromo,
    restaurer, ajouter, changerQuantite, vider, retenirSuivi, choisirCode,
  }
}
