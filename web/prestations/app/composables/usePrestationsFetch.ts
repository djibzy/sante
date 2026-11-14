import type { UseFetchOptions } from '#app'

/** Appel à l'API Prestations : adresse interne côté serveur, publique dans le navigateur. */
export function usePrestationsFetch<T>(chemin: string, options: UseFetchOptions<T> = {}) {
  const config = useRuntimeConfig()
  const baseURL = import.meta.server
    ? (config.apiPrestationsInterne as string) || config.public.apiPrestations
    : config.public.apiPrestations
  return useFetch(chemin, { baseURL, ...options } as UseFetchOptions<T>)
}
