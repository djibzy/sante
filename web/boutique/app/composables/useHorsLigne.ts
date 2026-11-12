/** État du réseau, suivi par le module hors ligne (vrai tant que l'on ne sait pas). */
export function useHorsLigne() {
  const enLigne = useState('en-ligne', () => true)
  return { enLigne }
}
