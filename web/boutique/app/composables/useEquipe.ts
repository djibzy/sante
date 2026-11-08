/** Accès aux écrans de l'équipe ; l'API vérifie aussi chaque rôle. */
export function useEquipe(roles: string[] = ['boutique:admin']) {
  const { attendre, aLeRole, utilisateur } = useSession()
  const verifie = ref(false)
  const autorise = computed(() => roles.some(role => aLeRole(role)))
  const estGestionnaire = computed(() => aLeRole('boutique:admin'))
  onMounted(async () => {
    await attendre()
    verifie.value = true
  })
  return { verifie, autorise, estGestionnaire, utilisateur }
}
