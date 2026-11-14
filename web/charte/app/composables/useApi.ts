/**
 * Appels à l'API d'un produit depuis le navigateur, avec le jeton de la session s'il existe.
 * Jeton d'accès expiré (15 minutes) : il est renouvelé une fois, puis l'appel est rejoué.
 */
export interface OptionsAppel {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: Record<string, unknown> | FormData
  query?: Record<string, unknown>
  responseType?: 'blob'
}

export function useApi(baseURL: string) {
  const { jeton, rafraichir } = useSession()

  function entetes(): Record<string, string> {
    return jeton.value ? { Authorization: `Bearer ${jeton.value}` } : {}
  }

  async function appeler<T>(chemin: string, options: OptionsAppel = {}): Promise<T> {
    const essai = () => $fetch<T>(chemin, { baseURL, ...options, headers: entetes() })
    try {
      return await essai()
    } catch (e) {
      if ((e as { status?: number }).status === 401 && jeton.value) {
        await rafraichir()
        return await essai()
      }
      throw e
    }
  }

  /** Télécharge un fichier protégé par la session (PDF, CSV). */
  async function telecharger(chemin: string, nomFichier: string) {
    const blob = await appeler<Blob>(chemin, { responseType: 'blob' })
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(blob)
    lien.download = nomFichier
    lien.click()
    setTimeout(() => URL.revokeObjectURL(lien.href), 60_000)
  }

  return { appeler, telecharger, url: (chemin: string) => `${baseURL}${chemin}` }
}
