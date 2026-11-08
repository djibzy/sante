<script setup lang="ts">
import type { Zone } from '~/types/commandes'

// Retrait gratuit à la boutique, ou livraison dans une zone desservie (frais affichés).
const props = defineProps<{ zones: Zone[]; adresseRequise?: boolean }>()
const { livraison } = usePanier()
watch(() => livraison.value.mode, (mode) => {
  if (mode === 'livraison' && !livraison.value.zone_id) livraison.value.zone_id = props.zones[0]?.id ?? null
})
</script>

<template>
  <fieldset class="livraison">
    <legend>Réception</legend>
    <label class="option" :class="{ actif: livraison.mode === 'retrait' }">
      <input v-model="livraison.mode" type="radio" value="retrait">
      <span><strong>Retrait à la boutique</strong><small>Gratuit, nous vous appelons quand c'est prêt</small></span>
    </label>
    <label class="option" :class="{ actif: livraison.mode === 'livraison' }">
      <input v-model="livraison.mode" type="radio" value="livraison" :disabled="!zones.length">
      <span><strong>Livraison</strong><small>Bamako et environs</small></span>
    </label>
    <template v-if="livraison.mode === 'livraison'">
      <div class="champ">
        <label for="zone">Zone</label>
        <select id="zone" v-model="livraison.zone_id">
          <option v-for="z in zones" :key="z.id" :value="z.id">
            {{ z.nom }} – {{ formaterFcfa(z.frais) }}
          </option>
        </select>
      </div>
      <div v-if="adresseRequise" class="champ">
        <label for="adresse">Adresse</label>
        <textarea id="adresse" v-model="livraison.adresse" maxlength="300" rows="2" required placeholder="Quartier, rue, porte, un repère connu" />
      </div>
    </template>
  </fieldset>
</template>

<style scoped>
.livraison { border: 0; padding: 0; margin: 0 0 8px; display: grid; gap: 8px; }
legend { font-weight: 700; margin-bottom: 8px; }
.option {
  display: flex; gap: 12px; align-items: flex-start; padding: 12px 14px; border: 1.5px solid var(--bordure);
  border-radius: 12px; cursor: pointer; background: var(--surface);
}
.option.actif { border-color: var(--primaire); background: var(--primaire-clair); }
.option input { margin-top: 4px; accent-color: var(--primaire); }
.option strong, .option small { display: block; }
.option small { color: var(--texte-doux); }
.champ { margin: 4px 0 0; }
</style>
