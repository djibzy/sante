// Le panier et les liens de suivi sont relus depuis l'appareil une fois l'hydratation
// terminée (mise en page comprise) : le rendu du serveur et celui du navigateur coïncident.
export default defineNuxtPlugin(() => {
  onNuxtReady(() => usePanier().restaurer())
})
