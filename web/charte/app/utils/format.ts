/** « 12500 » devient « 12 500 FCFA ». */
export function formaterFcfa(montant: number): string {
  return `${new Intl.NumberFormat('fr-FR').format(montant).replace(/ | /g, ' ')} FCFA`
}

const jour = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
const jourHeure = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Bamako',
})

/** « 2026-11-08 » devient « 8 novembre 2026 ». */
export function formaterDate(iso: string): string {
  const [annee, mois, j] = iso.slice(0, 10).split('-').map(Number)
  return jour.format(new Date(Date.UTC(annee!, mois! - 1, j!)))
}

/** Date et heure de Bamako : « 8 nov., 14:05 ». */
export function formaterDateHeure(iso: string): string {
  return jourHeure.format(new Date(iso))
}

/** « +22376123456 » devient « +223 76 12 34 56 » (numéros du Mali). */
export function formaterTelephone(e164: string): string {
  const mali = /^\+223(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(e164)
  return mali ? `+223 ${mali.slice(1).join(' ')}` : e164
}
