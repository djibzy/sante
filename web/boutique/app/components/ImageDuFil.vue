<script setup lang="ts">
// Image jointe à un message. Elle est privée : lue par l'API avec la clé du lien de suivi ou la
// session, puis affichée depuis la mémoire du navigateur (jamais par une adresse publique).
const props = defineProps<{ chemin: string, requete?: Record<string, string>, description: string }>()
const { appeler } = useApiBoutique()
const adresse = ref('')
const indisponible = ref(false)
const grande = ref(false)

onMounted(async () => {
  try {
    const image = await appeler<Blob>(props.chemin, { query: props.requete, responseType: 'blob' })
    adresse.value = URL.createObjectURL(image)
  } catch {
    indisponible.value = true
  }
})
onBeforeUnmount(() => {
  if (adresse.value) URL.revokeObjectURL(adresse.value)
})
</script>

<template>
  <button
    v-if="adresse" type="button" class="image" :class="{ grande }"
    :aria-label="grande ? 'Réduire l\'image' : 'Agrandir l\'image'" @click="grande = !grande"
  >
    <img :src="adresse" :alt="description">
  </button>
  <span v-else class="aide">{{ indisponible ? 'Image indisponible' : 'Chargement de l\'image…' }}</span>
</template>

<style scoped>
.image { display: block; padding: 0; border: 0; background: none; cursor: zoom-in; max-width: min(100%, 260px); border-radius: 10px; overflow: hidden; }
.image.grande { max-width: 100%; cursor: zoom-out; }
.image img { display: block; width: 100%; height: auto; }
</style>
