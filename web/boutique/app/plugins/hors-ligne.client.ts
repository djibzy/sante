// Travail hors ligne : le service worker (/sw.js, écrit à la construction) garde l'application
// et le catalogue sur l'appareil. L'état du réseau alimente le bandeau « hors ligne ».
export default defineNuxtPlugin(() => {
  const { enLigne } = useHorsLigne()
  onNuxtReady(() => {
    enLigne.value = navigator.onLine
    window.addEventListener('online', () => { enLigne.value = true })
    window.addEventListener('offline', () => { enLigne.value = false })
    if (!import.meta.dev && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // navigateur ou mode privé sans service worker : le site marche en ligne
      })
    }
  })
})
