// Le panier, les liens de suivi et les favoris sont relus depuis l'appareil une fois
// l'hydratation terminée (mise en page comprise) : le rendu du serveur et celui du
// navigateur coïncident.
export default defineNuxtPlugin(() => {
  onNuxtReady(() => {
    usePanier().restaurer()
    useFavoris().restaurer()
  })
})
