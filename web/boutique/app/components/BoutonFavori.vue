<script setup lang="ts">
const props = defineProps<{ slug: string; nom: string }>()
const { estFavori, basculer } = useFavoris()
const actif = computed(() => estFavori(props.slug))
</script>

<template>
  <button
    type="button" class="favori" :class="{ actif }" :aria-pressed="actif"
    :aria-label="actif ? `Retirer ${nom} des favoris` : `Ajouter ${nom} aux favoris`"
    @click.prevent="basculer(slug)"
  >
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20s-7-4.4-9.2-8.6C1.3 8.4 3 5 6.4 5c2 0 3.4 1.2 4 2.3.6-1.1 2-2.3 4-2.3C17.9 5 20 8 18.6 11.4 16.9 15.6 12 20 12 20z" />
    </svg>
  </button>
</template>

<style scoped>
.favori {
  width: 38px; height: 38px; border-radius: 50%; border: 0; display: grid; place-items: center; cursor: pointer;
  background: rgba(255, 255, 255, 0.92); box-shadow: 0 1px 4px rgba(23, 21, 58, 0.15);
}
.favori svg { fill: none; stroke: var(--texte); stroke-width: 1.8; max-width: none; }
.favori.actif svg { fill: var(--accent); stroke: var(--accent-texte); }
</style>
