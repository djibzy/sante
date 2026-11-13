<script setup lang="ts">
import type { Chiffrage } from '~/types/commandes'

// Code de réduction : saisi une fois, gardé avec le panier, vérifié par le serveur à chaque
// chiffrage (motif affiché s'il ne s'applique pas) puis de nouveau à la commande.
const props = defineProps<{ chiffrage: Chiffrage | null }>()
const { codePromo, choisirCode } = usePanier()
const saisie = ref('')
const ouvert = ref(false)
const accepte = computed(() => props.chiffrage?.code_promo ?? null)
const refus = computed(() => (codePromo.value ? props.chiffrage?.code_refuse ?? null : null))
function appliquer() {
  if (saisie.value.trim()) choisirCode(saisie.value)
}
function retirer() {
  choisirCode('')
  saisie.value = ''
}
</script>

<template>
  <div class="code-promo">
    <p v-if="accepte" class="accepte" role="status">
      <span><strong>{{ accepte }}</strong> : {{ chiffrage?.libelle_promo }}</span>
      <button type="button" class="bouton bouton-discret" @click="retirer">Retirer le code</button>
    </p>
    <template v-else>
      <button v-if="!ouvert && !codePromo" type="button" class="lien" :aria-expanded="ouvert" @click="ouvert = true">
        Vous avez un code promo ?
      </button>
      <form v-else class="saisie" @submit.prevent="appliquer">
        <label for="code-promo" class="visuellement-cache">Code promo</label>
        <input
          id="code-promo" v-model="saisie" maxlength="30" autocomplete="off" autocapitalize="characters"
          spellcheck="false" placeholder="Code promo"
        >
        <button type="submit" class="bouton bouton-secondaire">Appliquer</button>
      </form>
      <p v-if="refus" class="alerte alerte-erreur refus" role="alert">
        {{ codePromo }} : {{ refus }}
        <button type="button" class="bouton bouton-discret" @click="retirer">Retirer le code</button>
      </p>
    </template>
  </div>
</template>

<style scoped>
.code-promo { display: grid; gap: 8px; }
.lien { justify-self: start; padding: 0; border: 0; background: none; color: var(--primaire); font: inherit; font-weight: 650; text-decoration: underline; cursor: pointer; }
.saisie { display: flex; gap: 8px; }
.saisie input { flex: 1; min-width: 0; min-height: 44px; padding: 0 10px; border: 1.5px solid var(--bordure); border-radius: 10px; font: inherit; text-transform: uppercase; }
.accepte { margin: 0; display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 10px; background: var(--succes-clair); color: var(--succes); font-size: 0.92rem; }
.refus { margin: 0; display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 0.92rem; }
</style>
