/**
 * Installation de Bibou sur l'écran d'accueil du téléphone (application web) : le navigateur
 * propose l'installation une fois le site visité ; on garde sa proposition pour un bouton.
 */
interface ProposeInstallation extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

let proposition: ProposeInstallation | null = null

export function useInstallation() {
  const possible = useState('installation-possible', () => false)
  const installee = useState('installation-faite', () => false)
  const iphone = useState('installation-iphone', () => false)

  function suivre() {
    installee.value = window.matchMedia('(display-mode: standalone)').matches
      || (navigator as Navigator & { standalone?: boolean }).standalone === true
    // Safari sur iPhone n'a pas de bouton : on explique le geste à faire.
    iphone.value = /iPhone|iPad|iPod/.test(navigator.userAgent) && !installee.value
    window.addEventListener('beforeinstallprompt', (evenement) => {
      evenement.preventDefault()
      proposition = evenement as ProposeInstallation
      possible.value = true
    })
    window.addEventListener('appinstalled', () => {
      installee.value = true
      possible.value = false
    })
  }

  async function installer() {
    if (!proposition) return
    await proposition.prompt()
    const { outcome } = await proposition.userChoice
    proposition = null
    possible.value = false
    installee.value = outcome === 'accepted'
  }

  return { possible, installee, iphone, suivre, installer }
}
