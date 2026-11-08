// Au chargement, on reprend la session si le cookie de rafraîchissement est encore valide.
export default defineNuxtPlugin(() => {
  const { jeton, rafraichir } = useSession()
  if (!jeton.value) void rafraichir()
})
