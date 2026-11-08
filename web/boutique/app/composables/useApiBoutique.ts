/** Appels à l'API de la boutique depuis le navigateur, avec le jeton de la session s'il existe. */
interface Options {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: Record<string, unknown>
  query?: Record<string, unknown>
  responseType?: 'blob'
}

export function useApiBoutique() {
  const config = useRuntimeConfig()
  const { jeton, rafraichir } = useSession()

  function entetes(): Record<string, string> {
    return jeton.value ? { Authorization: `Bearer ${jeton.value}` } : {}
  }

  async function appeler<T>(chemin: string, options: Options = {}): Promise<T> {
    const essai = () => $fetch<T>(chemin, {
      baseURL: config.public.apiBoutique, ...options, headers: entetes(),
    })
    try {
      return await essai()
    } catch (e) {
      // Jeton d'accès expiré (15 minutes) : on le renouvelle une fois, puis on réessaie.
      if ((e as { status?: number }).status === 401 && jeton.value) {
        await rafraichir()
        return await essai()
      }
      throw e
    }
  }

  /** Télécharge un fichier protégé par la session (devis PDF). */
  async function telecharger(chemin: string, nomFichier: string) {
    const blob = await appeler<Blob>(chemin, { responseType: 'blob' })
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(blob)
    lien.download = nomFichier
    lien.click()
    setTimeout(() => URL.revokeObjectURL(lien.href), 60_000)
  }

  return { appeler, telecharger, url: (chemin: string) => `${config.public.apiBoutique}${chemin}` }
}
