/** Dates de la tournée, à l'heure de Bamako (UTC toute l'année). */
export const JOURS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']

export function aujourdHui(): string {
  return new Date().toISOString().slice(0, 10)
}

export function decaler(jour: string, nombre: number): string {
  const date = new Date(`${jour}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + nombre)
  return date.toISOString().slice(0, 10)
}

/** « 2026-11-19 » : « jeu. 19/11 ». */
export function jourCourt(jour: string): string {
  const date = new Date(`${jour}T12:00:00Z`)
  const nom = JOURS[(date.getUTCDay() + 6) % 7]!.slice(0, 3)
  return `${nom}. ${jour.slice(8, 10)}/${jour.slice(5, 7)}`
}

export function moisCourant(): string {
  return aujourdHui().slice(0, 7)
}
