/** Accès aux écrans de l'équipe : rôle boutique:admin, vérifié aussi par l'API. */
export function useEquipe() {
  const { attendre, aLeRole, utilisateur } = useSession()
  const verifie = ref(false)
  const autorise = computed(() => aLeRole('boutique:admin'))
  onMounted(async () => {
    await attendre()
    verifie.value = true
  })
  return { verifie, autorise, utilisateur }
}
