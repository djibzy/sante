/**
 * Session de la personne connectée.
 *
 * Le jeton d'accès reste en mémoire ; le jeton de rafraîchissement vit dans un cookie
 * httpOnly posé par le service Comptes, invisible pour le JavaScript de la page.
 */
export interface Utilisateur {
  id: string
  nom: string
  telephone: string
  langue: string
  roles: string[]
}

interface ReponseJetons {
  jeton_acces: string
  utilisateur: Utilisateur
}

// Un seul rafraîchissement à la fois : le jeton de rafraîchissement est à usage unique, deux
// envois simultanés feraient croire à un vol et couperaient toutes les sessions.
let rafraichissementEnCours: Promise<void> | null = null

export function useSession() {
  const config = useRuntimeConfig()
  const jeton = useState<string | null>('jeton', () => null)
  const utilisateur = useState<Utilisateur | null>('utilisateur', () => null)
  const prete = useState('session-prete', () => false)

  const appeler = <T>(chemin: string, body?: Record<string, unknown>) =>
    $fetch<T>(chemin, {
      baseURL: config.public.apiComptes,
      method: 'POST',
      body,
      credentials: 'include',
      headers: { 'X-Client': 'web' },
    })

  function ouvrir(reponse: ReponseJetons) {
    jeton.value = reponse.jeton_acces
    utilisateur.value = reponse.utilisateur
    prete.value = true
  }

  function fermer() {
    jeton.value = null
    utilisateur.value = null
  }

  async function connexion(telephone: string, motDePasse: string) {
    ouvrir(await appeler<ReponseJetons>('/api/v1/auth/connexion', {
      telephone, mot_de_passe: motDePasse, appareil: 'navigateur',
    }))
  }

  async function inscription(donnees: Record<string, unknown>) {
    ouvrir(await appeler<ReponseJetons>('/api/v1/auth/inscription', donnees))
  }

  function rafraichir(): Promise<void> {
    rafraichissementEnCours ??= appeler<ReponseJetons>('/api/v1/auth/rafraichir')
      .then(ouvrir)
      .catch(fermer)
      .finally(() => {
        prete.value = true
        rafraichissementEnCours = null
      })
    return rafraichissementEnCours
  }

  /** Attend que la session ait été reprise au chargement de la page (ou constatée absente). */
  async function attendre() {
    if (!prete.value) await rafraichir()
  }

  async function deconnexion() {
    try {
      await appeler('/api/v1/auth/deconnexion')
    } finally {
      fermer()
    }
  }

  // Même règle que l'API : l'administrateur général a tous les rôles.
  const aLeRole = (role: string) => {
    const roles = utilisateur.value?.roles ?? []
    return roles.includes(role) || roles.includes('admin')
  }

  return { jeton, utilisateur, prete, connexion, inscription, rafraichir, attendre, deconnexion, aLeRole }
}

/** Message lisible à partir d'une erreur renvoyée par une API. */
export function messageErreur(erreur: unknown): string {
  const detail = (erreur as { data?: { detail?: unknown } })?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Vérifiez les champs du formulaire.'
  return 'Le service ne répond pas. Vérifiez votre connexion et réessayez.'
}

/** Chemin de retour après connexion : seulement un chemin interne au site. */
export function cheminDeRetour(valeur: unknown): string {
  return typeof valeur === 'string' && valeur.startsWith('/') && !valeur.startsWith('//')
    ? valeur
    : '/'
}
