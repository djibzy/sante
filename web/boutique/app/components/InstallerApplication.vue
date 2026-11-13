<script setup lang="ts">
const { possible, installee, iphone, installer } = useInstallation()
</script>

<template>
  <div v-if="!installee && (possible || iphone)" class="installation">
    <button v-if="possible" type="button" class="bouton bouton-secondaire" @click="installer">
      Installer Bibou sur ce téléphone
    </button>
    <p v-else class="aide">
      Pour installer Bibou sur votre iPhone : touchez « Partager », puis « Sur l'écran d'accueil ».
    </p>
    <p class="aide">L'application s'ouvre d'un geste et garde le catalogue enregistré, même sans réseau.</p>
  </div>
</template>

<style scoped>
.installation { display: grid; gap: 6px; justify-items: start; }
.installation p { margin: 0; }
</style>
