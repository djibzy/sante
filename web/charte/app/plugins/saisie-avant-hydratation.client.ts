/**
 * Réseau lent : la page s'affiche avant que ses scripts soient arrivés. Ce que la personne tape
 * pendant ce temps serait effacé au moment où la page devient interactive (hydratation) : Vue
 * remet chaque champ à la valeur de l'application, vide. Ce greffon relève les champs remplis à
 * la main avant ce moment, les rétablit une fois la page prête (avec les événements qui mettent
 * l'application à jour), et rejoue l'envoi d'un formulaire tenté trop tôt, retenu par le petit
 * script placé en tête de page (nuxt.config.ts de la charte).
 *
 * Seuls les champs qui portent un identifiant (id) sont suivis : c'est le cas de tous nos
 * formulaires, dont chaque champ a son étiquette.
 */
type Champ = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
interface Saisie { valeur: string; coche: boolean; choix: string[] }
interface FenetreEnvoi { __envoiRetenu?: HTMLFormElement; __libererEnvois?: () => void }

const IGNORES = new Set(['file', 'hidden', 'submit', 'button', 'reset', 'image'])

function estChamp(cible: EventTarget | null): cible is Champ {
  return cible instanceof HTMLInputElement || cible instanceof HTMLTextAreaElement
    || cible instanceof HTMLSelectElement
}

function caseOuBouton(champ: Champ): champ is HTMLInputElement {
  return champ instanceof HTMLInputElement && (champ.type === 'checkbox' || champ.type === 'radio')
}

/** Rempli à la main : sa valeur n'est plus celle que le serveur a envoyée. */
function modifie(champ: Champ): boolean {
  if (champ instanceof HTMLSelectElement) {
    return [...champ.options].some(option => option.selected !== option.defaultSelected)
  }
  if (caseOuBouton(champ)) return champ.checked !== champ.defaultChecked
  return champ.value !== champ.defaultValue
}

export default defineNuxtPlugin({
  name: 'saisie-avant-hydratation',
  enforce: 'pre',
  setup(nuxtApp) {
    const fenetre = window as Window & FenetreEnvoi
    if (!nuxtApp.isHydrating) {
      fenetre.__libererEnvois?.()
      return
    }
    const saisies = new Map<string, Saisie>()

    function relever(cible: EventTarget | null) {
      if (!estChamp(cible) || !cible.id || (cible instanceof HTMLInputElement && IGNORES.has(cible.type))) return
      saisies.set(cible.id, {
        valeur: cible.value,
        coche: caseOuBouton(cible) && cible.checked,
        choix: cible instanceof HTMLSelectElement ? [...cible.selectedOptions].map(o => o.value) : [],
      })
    }
    const surSaisie = (evenement: Event) => relever(evenement.target)

    document.querySelectorAll<Champ>('input, textarea, select').forEach((champ) => {
      if (modifie(champ)) relever(champ)
    })
    document.addEventListener('input', surSaisie, true)
    document.addEventListener('change', surSaisie, true)

    nuxtApp.hooks.hookOnce('app:suspense:resolve', () => {
      document.removeEventListener('input', surSaisie, true)
      document.removeEventListener('change', surSaisie, true)
      // Après les effets de l'hydratation (valeurs remises par Vue), dans la tâche suivante.
      setTimeout(() => {
        for (const [id, saisie] of saisies) {
          const champ = document.getElementById(id)
          if (!estChamp(champ)) continue
          if (caseOuBouton(champ)) {
            // Un bouton radio décoché se déduit du bouton coché du même groupe.
            if (champ.type === 'radio' && !saisie.coche) continue
            if (champ.checked !== saisie.coche) {
              champ.checked = saisie.coche
              champ.dispatchEvent(new Event('change', { bubbles: true }))
            }
          } else if (champ instanceof HTMLSelectElement) {
            for (const option of champ.options) option.selected = saisie.choix.includes(option.value)
            champ.dispatchEvent(new Event('change', { bubbles: true }))
          } else if (champ.value !== saisie.valeur) {
            champ.value = saisie.valeur
            champ.dispatchEvent(new Event('input', { bubbles: true }))
          }
        }
        fenetre.__libererEnvois?.()
        const retenu = fenetre.__envoiRetenu
        delete fenetre.__envoiRetenu
        if (retenu?.isConnected) retenu.requestSubmit()
      })
    })
  },
})
