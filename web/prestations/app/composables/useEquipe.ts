/** Accès à l'espace de l'équipe ; l'API vérifie aussi chaque rôle. */
export const GESTION = 'prestations:admin'
export const TERRAIN = 'prestations:terrain'

export function useEquipe() {
  const { attendre, aLeRole, utilisateur } = useSession()
  const verifie = ref(false)
  const autorise = computed(() => aLeRole(GESTION) || aLeRole(TERRAIN))
  const estGestionnaire = computed(() => aLeRole(GESTION))
  onMounted(async () => {
    await attendre()
    verifie.value = true
  })
  return { verifie, autorise, estGestionnaire, utilisateur }
}
