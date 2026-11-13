// Travail hors ligne : le service worker (/sw.js, écrit à la construction) garde l'application
// et le catalogue sur l'appareil ; une commande préparée sans réseau part à son retour.
export default defineNuxtPlugin(() => {
  const { enLigne } = useHorsLigne()
  const differe = useEnvoiDiffere()
  const installation = useInstallation()
  onNuxtReady(() => {
    installation.suivre()
    enLigne.value = navigator.onLine
    differe.restaurer()
    if (navigator.onLine) void differe.tenter()
    window.addEventListener('online', () => {
      enLigne.value = true
      void differe.tenter()
    })
    window.addEventListener('offline', () => { enLigne.value = false })
    if (!import.meta.dev && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // navigateur ou mode privé sans service worker : le site marche en ligne
      })
    }
  })
})
