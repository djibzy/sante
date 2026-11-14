/** Appels à l'API Prestations depuis le navigateur (voir useApi, dans la charte commune). */
export function useApiPrestations() {
  return useApi(useRuntimeConfig().public.apiPrestations)
}
