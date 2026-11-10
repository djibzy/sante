/** Favoris gardés sur l'appareil (sans compte), comme dans une boutique de mode. */
const CLE = 'bibou-favoris'

export function useFavoris() {
  const slugs = useState<string[]>('favoris', () => [])
  const nombre = computed(() => slugs.value.length)

  function restaurer() {
    try {
      const brut = localStorage.getItem(CLE)
      slugs.value = brut ? (JSON.parse(brut) as string[]).slice(0, 50) : []
    } catch {
      slugs.value = []
    }
  }

  function basculer(slug: string) {
    slugs.value = slugs.value.includes(slug) ? slugs.value.filter(s => s !== slug) : [slug, ...slugs.value].slice(0, 50)
    try {
      localStorage.setItem(CLE, JSON.stringify(slugs.value))
    } catch {
      // Stockage indisponible : les favoris restent le temps de la visite.
    }
  }

  return { slugs, nombre, restaurer, basculer, estFavori: (slug: string) => slugs.value.includes(slug) }
}
