import type { UseFetchOptions } from '#app'

/** Appel à l'API de la boutique : adresse interne côté serveur, publique dans le navigateur. */
export function useBoutiqueFetch<T>(chemin: string | (() => string), options: UseFetchOptions<T> = {}) {
  const config = useRuntimeConfig()
  const baseURL = import.meta.server
    ? (config.apiBoutiqueInterne as string) || config.public.apiBoutique
    : config.public.apiBoutique
  return useFetch(chemin, { baseURL, ...options } as UseFetchOptions<T>)
}
