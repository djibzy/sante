/** Les photos envoyées par l'équipe sont servies par l'API (/medias/…) : on complète leur
 * adresse ; les autres (https://…) restent telles quelles. */
export function useAdresseImage() {
  const base = useRuntimeConfig().public.apiBoutique
  return (url: string) => (url.startsWith('/medias/') ? `${base}${url}` : url)
}
