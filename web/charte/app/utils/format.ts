/** « 12500 » devient « 12 500 FCFA ». */
export function formaterFcfa(montant: number): string {
  return `${new Intl.NumberFormat('fr-FR').format(montant).replace(/ | /g, ' ')} FCFA`
}
