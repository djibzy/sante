/** Appels à l'API de la boutique depuis le navigateur (voir useApi, dans la charte commune). */
export function useApiBoutique() {
  return useApi(useRuntimeConfig().public.apiBoutique)
}
