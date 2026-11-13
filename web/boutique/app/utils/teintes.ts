/**
 * Teintes dérivées d'une couleur « #rrggbb » : ombres et reflets des illustrations d'articles,
 * fond des tuiles de la page « Explorer ».
 */
function versRvb(hexa: string): [number, number, number] {
  const n = Number.parseInt(hexa.slice(1, 7), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function versHexa(rvb: number[]): string {
  return `#${rvb.map(c => Math.round(Math.max(0, Math.min(255, c))).toString(16).padStart(2, '0')).join('')}`
}

/** Mélange de deux couleurs : `part` de 0 (la première) à 1 (la seconde). */
export function melanger(hexa: string, autre: string, part: number): string {
  const a = versRvb(hexa)
  const b = versRvb(autre)
  return versHexa(a.map((c, i) => c + (b[i]! - c) * part))
}

/** Luminance relative (WCAG), de 0 (noir) à 1 (blanc). */
export function luminance(hexa: string): number {
  const [r, g, b] = versRvb(hexa).map((c) => {
    const v = c / 255
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }) as [number, number, number]
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Couleur claire : un trait foncé la détache d'un fond clair. */
export function estClaire(hexa: string): boolean {
  return luminance(hexa) > 0.55
}

export const HEXA = /^#[0-9a-f]{6}$/i

/**
 * Forme dessinée d'un article (illustration en attendant ses photos), d'après son rayon et
 * son adresse ; null : pas de dessin, le pictogramme du rayon le remplace.
 */
export function formeArticle(rayon: string, slug: string): string | null {
  if (rayon === 'blouses-medicales') return 'blouse'
  if (rayon === 'tuniques') return 'tunique'
  if (rayon === 'pantalons') return slug.includes('cargo') ? 'pantalon-cargo' : 'pantalon'
  if (rayon === 'tenues-de-bloc') return slug.includes('calot') ? 'calot' : 'tenue-de-bloc'
  if (rayon === 'chaussures') return slug.includes('sabot') ? 'sabot' : 'basket'
  if (rayon === 'gilets-polos') return slug.includes('polo') ? 'polo' : 'gilet'
  if (rayon === 'accessoires' && slug.includes('montre')) return 'montre'
  if (rayon === 'campagnes' && slug.includes('shirt')) return 'tshirt'
  return null
}
