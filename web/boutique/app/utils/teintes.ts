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

/** « #rrggbb » vers OKLab (comme le service : boutique.couleurs). */
export function oklab(hexa: string): [number, number, number] {
  const [r, g, b] = versRvb(hexa).map((c) => {
    const v = c / 255
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }) as [number, number, number]
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ]
}

/** Écart perçu entre deux couleurs, de 0 (identiques) à 100 (noir et blanc). */
export function ecart(une: string, autre: string): number {
  const a = oklab(une)
  const b = oklab(autre)
  return 100 * Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

/** Blanc, gris, noir ou bleu marine : se marie avec toutes les couleurs. */
export function estNeutre(hexa: string): boolean {
  const [clarte, a, b] = oklab(hexa)
  return Math.hypot(a, b) < 0.035 || clarte < 0.33
}

/**
 * Couleurs dominantes d'une photo, calculées dans le navigateur : la photo ne quitte pas le
 * téléphone. Le centre compte plus que les bords (le vêtement est d'ordinaire au centre, le mur
 * ou le sol autour) ; les teintes voisines sont regroupées. De la plus présente à la moins
 * présente.
 */
export async function couleursDominantes(fichier: Blob, nombre = 4): Promise<string[]> {
  const adresse = URL.createObjectURL(fichier)
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image()
      element.onload = () => resolve(element)
      element.onerror = () => reject(new Error('Photo illisible'))
      element.src = adresse
    })
    const cote = 72
    const toile = document.createElement('canvas')
    toile.width = cote
    toile.height = cote
    const contexte = toile.getContext('2d', { willReadFrequently: true })
    if (!contexte) throw new Error('Photo illisible')
    const marge = 0.12 // bords de la photo laissés de côté
    const { naturalWidth: largeur, naturalHeight: hauteur } = image
    contexte.drawImage(image, largeur * marge, hauteur * marge, largeur * (1 - 2 * marge), hauteur * (1 - 2 * marge), 0, 0, cote, cote)
    const { data } = contexte.getImageData(0, 0, cote, cote)
    const cases = new Map<number, { poids: number, r: number, g: number, b: number }>()
    for (let y = 0; y < cote; y++) {
      for (let x = 0; x < cote; x++) {
        const i = (y * cote + x) * 4
        if (data[i + 3]! < 128) continue
        const [r, g, b] = [data[i]!, data[i + 1]!, data[i + 2]!]
        const dx = (x - cote / 2) / (cote / 2)
        const dy = (y - cote / 2) / (cote / 2)
        const poids = Math.exp(-(dx * dx + dy * dy) * 1.5)
        const cle = ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
        const case_ = cases.get(cle) ?? { poids: 0, r: 0, g: 0, b: 0 }
        case_.poids += poids
        case_.r += r * poids
        case_.g += g * poids
        case_.b += b * poids
        cases.set(cle, case_)
      }
    }
    const groupes: { poids: number, hex: string }[] = []
    const triees = [...cases.values()].sort((a, b) => b.poids - a.poids)
    for (const c of triees) {
      const hex = versHexa([c.r / c.poids, c.g / c.poids, c.b / c.poids])
      const voisin = groupes.find(g => ecart(g.hex, hex) < 9)
      if (voisin) voisin.poids += c.poids
      else if (groupes.length < 16) groupes.push({ poids: c.poids, hex })
    }
    return groupes.sort((a, b) => b.poids - a.poids).slice(0, nombre).map(g => g.hex)
  } finally {
    URL.revokeObjectURL(adresse)
  }
}
