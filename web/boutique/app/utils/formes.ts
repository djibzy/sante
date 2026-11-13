/**
 * Formes des articles dessinés (vue de face, ou de profil pour les chaussures), dans un cadre de
 * 100 × 125 : utilisées seules (IllustrationArticle) ou habillant le mannequin (« Composer ma
 * tenue »). « base » est la couleur de l'article ; les autres teintes en dérivent.
 */
/** Pièce posée sur le mannequin : sa forme, sa couleur (et son nom, pour le wax). */
export interface PieceHabillee {
  forme: string
  hex: string
  couleur?: string | null
  brode?: boolean
}

export interface Trace {
  d: string
  remplissage?: 'base' | 'ombre' | 'clair' | 'col' | 'semelle' | 'cadran' | 'aucun'
  trait?: 'contour' | 'detail' | 'fil' | 'aucun'
  epaisseur?: number
  pointille?: boolean
  corps?: boolean // reçoit le motif wax et le modelé
  transform?: string
}

const TUNIQUE: Trace[] = [
  { d: 'M40 17L27 21L11 43L22 52L29 45L28 104Q50 108 72 104L71 45L78 52L89 43L73 21L60 17L50 35Z', remplissage: 'base', trait: 'contour', corps: true },
  { d: 'M40 17L50 35L60 17', trait: 'detail', epaisseur: 2.6 },
  { d: 'M14 40.5L24.5 49M86 40.5L75.5 49', trait: 'detail' },
  { d: 'M58 54h11v9q-5.5 2-11 0Z', trait: 'detail' },
  { d: 'M29 97l.5 7M71 97l-.5 7', trait: 'detail' },
]
const PANTALON: Trace[] = [
  { d: 'M30 10L70 10L73 118L55 118L50 50L45 118L27 118Z', remplissage: 'base', trait: 'contour', corps: true },
  { d: 'M30 17L70 17', trait: 'detail', epaisseur: 1.6 },
  { d: 'M48 17q-1 6-3 10M52 17q1 6 3 10', trait: 'detail' },
  { d: 'M31 19q5 7 2 15M69 19q-5 7-2 15', trait: 'detail' },
  { d: 'M28 112h17M55 112h17', trait: 'detail' },
]
const CARGO: Trace[] = [
  { d: 'M29 62h10v15h-10ZM61 62h10v15h-10Z', trait: 'detail' },
  { d: 'M29 66h10M61 66h10', trait: 'detail' },
]
export const FORMES: Record<string, Trace[]> = {
  tunique: TUNIQUE,
  pantalon: PANTALON,
  'pantalon-cargo': [...PANTALON, ...CARGO],
  blouse: [
    { d: 'M41 14L26 19L13 70L24 73L31 38L27 117L73 117L69 38L76 73L87 70L74 19L59 14Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M41 14L50 48L59 14Q50 18 41 14Z', remplissage: 'col', trait: 'aucun' },
    { d: 'M41 14L35 22L44 40L50 48M59 14L65 22L56 40L50 48', remplissage: 'aucun', trait: 'contour' },
    { d: 'M50 48L50 117', trait: 'detail' },
    { d: 'M31 84h13v13h-13ZM56 84h13v13h-13ZM33 47h9', trait: 'detail' },
    { d: 'M14.5 66L25 69M85.5 66L75 69', trait: 'detail' },
    { d: 'M52.5 58v.1M52.5 72v.1M52.5 86v.1M52.5 100v.1', trait: 'detail', epaisseur: 3.2 },
  ],
  'tenue-de-bloc': [
    ...PANTALON.map(t => ({ ...t, transform: 'translate(24 52) scale(.52)' })),
    ...TUNIQUE.map(t => ({ ...t, transform: 'translate(19 -6) scale(.62)' })),
  ],
  gilet: [
    { d: 'M40 14L26 19L12 74L23 77L30 40L29 104L71 104L70 40L77 77L88 74L74 19L60 14Q50 19 40 14Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M39 9Q50 14 61 9L61 15Q50 20 39 15Z', remplissage: 'ombre', trait: 'contour' },
    { d: 'M50 18L50 104', trait: 'detail', epaisseur: 1.8 },
    { d: 'M48.8 22h2.4v6h-2.4Z', remplissage: 'ombre', trait: 'detail' },
    { d: 'M34 74l6 12M66 74l-6 12M29 99h42', trait: 'detail' },
    { d: 'M13.5 70L24 73M86.5 70L76 73', trait: 'detail' },
  ],
  polo: [
    { d: 'M40 15L27 20L12 41L22 50L29 44L29 102L71 102L71 44L78 50L88 41L73 20L60 15Q50 20 40 15Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M47.5 20h5v18h-5Z', remplissage: 'aucun', trait: 'detail' },
    { d: 'M40 15L45 27L50 21L55 27L60 15Q50 20 40 15Z', remplissage: 'clair', trait: 'contour' },
    { d: 'M50 27v.1M50 33v.1', trait: 'detail', epaisseur: 2.6 },
    { d: 'M14 38.5L24 47M86 38.5L76 47', trait: 'detail' },
  ],
  tshirt: [
    { d: 'M40 15L27 20L12 41L22 50L29 44L29 102L71 102L71 44L78 50L88 41L73 20L60 15Q50 24 40 15Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M40 15Q50 24 60 15', trait: 'detail', epaisseur: 2.4 },
    { d: 'M14 38.5L24 47M86 38.5L76 47', trait: 'detail' },
  ],
  calot: [
    { d: 'M18 74Q18 38 50 36Q82 38 82 74Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M16 70h68v10q0 2-2 2h-64q-2 0-2-2Z', remplissage: 'ombre', trait: 'contour' },
    { d: 'M80 81q8 8 6 18M77 82q4 10-1 18', trait: 'contour', epaisseur: 2.2 },
    { d: 'M50 37v33', trait: 'detail' },
  ],
  sabot: [
    { d: 'M14 74Q10 56 26 52', trait: 'contour', epaisseur: 4 },
    { d: 'M12 88L12 76Q13 60 32 56L58 50Q78 46 87 62Q91 70 89 80L89 88Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M10 87h82v7q0 3-3 3h-76q-3 0-3-3Z', remplissage: 'semelle', trait: 'contour' },
    { d: 'M60 58v.1M68 57v.1M76 60v.1M64 64v.1M72 65v.1', trait: 'detail', epaisseur: 3.4 },
  ],
  basket: [
    // De profil, pointe à droite : talon et col à gauche, languette, laçage, bout renforcé.
    { d: 'M10 89Q8 72 13 63Q15 59 20 60L33 62Q37 52 46 51Q50 51 52 54L62 61Q78 69 88 76Q93 80 92 89Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M19 61Q26 67 33 62', remplissage: 'col', trait: 'contour' },
    { d: 'M7 88h86q2 0 2 2v4q0 4-4 4h-81q-4 0-4-4v-4q0-2 1-2Z', remplissage: 'semelle', trait: 'contour' },
    { d: 'M47 57l5 4M52 59l5 4M57 61.5l5 4', trait: 'detail', epaisseur: 1.6 },
    { d: 'M76 71Q79 80 92 83M14 82h70', trait: 'detail' },
  ],
  montre: [
    { d: 'M43 18h14v18q0 3-3 3h-8q-3 0-3-3Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M50 39v7', trait: 'contour', epaisseur: 2.4 },
    { d: 'M75 71a25 25 0 1 1-50 0a25 25 0 1 1 50 0Z', remplissage: 'base', trait: 'contour', corps: true },
    { d: 'M68 71a18 18 0 1 1-36 0a18 18 0 1 1 36 0Z', remplissage: 'cadran', trait: 'detail' },
    { d: 'M50 56v3M50 83v3M35 71h3M62 71h3', trait: 'detail', epaisseur: 1.6 },
    { d: 'M50 71V61M50 71l7 4', trait: 'contour', epaisseur: 1.8 },
  ],
}
// Broderie du nom sur la poitrine (côté cœur), selon la forme.
export const BRODERIES: Record<string, string> = {
  blouse: 'M56 46h11',
  tunique: 'M58 49h11',
  polo: 'M58 40h10',
  'tenue-de-bloc': 'M55 25h7',
  gilet: 'M55 36h10',
}

/** Place d'un article dans « Composer ma tenue », d'après sa forme. */
export const PIECE_DE_FORME: Record<string, string> = {
  tunique: 'haut',
  polo: 'haut',
  tshirt: 'haut',
  pantalon: 'bas',
  'pantalon-cargo': 'bas',
  blouse: 'dessus',
  gilet: 'dessus',
  basket: 'chaussures',
  sabot: 'chaussures',
  calot: 'calot',
}
