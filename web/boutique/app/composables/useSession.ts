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

export function useSession() {
  const config = useRuntimeConfig()
  const jeton = useState<string | null>('jeton', () => null)
  const utilisateur = useState<Utilisateur | null>('utilisateur', () => null)

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

  async function rafraichir() {
    try {
      ouvrir(await appeler<ReponseJetons>('/api/v1/auth/rafraichir'))
    } catch {
      fermer()
    }
  }

  async function deconnexion() {
    try {
      await appeler('/api/v1/auth/deconnexion')
    } finally {
      fermer()
    }
  }

  return { jeton, utilisateur, connexion, inscription, rafraichir, deconnexion }
}

/** Message lisible à partir d'une erreur renvoyée par une API. */
export function messageErreur(erreur: unknown): string {
  const detail = (erreur as { data?: { detail?: unknown } })?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Vérifiez les champs du formulaire.'
  return 'Le service ne répond pas. Vérifiez votre connexion et réessayez.'
}
