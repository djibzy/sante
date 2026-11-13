/**
 * Mesures du corps par taille (en centimètres) et taille conseillée d'après ses mesures : la plus
 * grande des tailles que demandent la poitrine, la taille et les hanches. Entre deux tailles (une
 * mesure dans le dernier centimètre de sa fourchette), la suivante est signalée.
 */
export interface Mesures { taille: string, poitrine: [number, number], tour: [number, number], hanches: [number, number] }

export const MESURES_HAUTS: Mesures[] = [
  { taille: 'XS', poitrine: [80, 84], tour: [64, 68], hanches: [88, 92] },
  { taille: 'S', poitrine: [85, 90], tour: [69, 74], hanches: [93, 98] },
  { taille: 'M', poitrine: [91, 96], tour: [75, 80], hanches: [99, 104] },
  { taille: 'L', poitrine: [97, 102], tour: [81, 86], hanches: [105, 110] },
  { taille: 'XL', poitrine: [103, 108], tour: [87, 92], hanches: [111, 116] },
  { taille: 'XXL', poitrine: [109, 116], tour: [93, 100], hanches: [117, 124] },
  { taille: 'XXXL', poitrine: [117, 124], tour: [101, 108], hanches: [125, 132] },
]

export const POINTURES: [string, number][] = [
  ['36', 23], ['37', 23.7], ['38', 24.3], ['39', 25], ['40', 25.7], ['41', 26.3], ['42', 27], ['43', 27.7], ['44', 28.3], ['45', 29],
]

type Mesure = 'poitrine' | 'tour' | 'hanches'

/** Rang de la taille qui couvre la mesure (fourchettes contiguës), ou -1 au-delà de la plus grande. */
function rang(mesure: Mesure, valeur: number): number {
  return MESURES_HAUTS.findIndex(m => valeur <= m[mesure][1])
}

export interface Conseil { taille: string, ou?: string, horsGuide?: boolean }

export function tailleConseillee(mesures: Partial<Record<Mesure, number | null>>): Conseil | null {
  const saisies = (Object.entries(mesures) as [Mesure, number | null | undefined][])
    .filter((e): e is [Mesure, number] => typeof e[1] === 'number' && e[1] >= 40 && e[1] <= 200)
  if (!saisies.length) return null
  const rangs = saisies.map(([mesure, valeur]) => rang(mesure, valeur))
  if (rangs.includes(-1)) return { taille: MESURES_HAUTS.at(-1)!.taille, horsGuide: true }
  const choisi = Math.max(...rangs)
  const limite = saisies.some(([mesure, valeur], i) => rangs[i] === choisi && valeur > MESURES_HAUTS[choisi]![mesure][1] - 1)
  const suivante = MESURES_HAUTS[choisi + 1]
  return { taille: MESURES_HAUTS[choisi]!.taille, ou: limite && suivante ? suivante.taille : undefined }
}

/** Pointure dont la longueur couvre le pied (au demi-centimètre près, sans serrer). */
export function pointureConseillee(longueur: number | null | undefined): Conseil | null {
  if (typeof longueur !== 'number' || longueur < 15 || longueur > 35) return null
  const trouvee = POINTURES.find(([, cm]) => longueur <= cm)
  return trouvee ? { taille: trouvee[0] } : { taille: POINTURES.at(-1)![0], horsGuide: true }
}
