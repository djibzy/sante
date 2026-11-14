<script setup lang="ts">
// Page de la structure, ouverte depuis le lien reçu par SMS : ses messages avec Yasal Santé. La
// clé du lien dit qui elle est ; la page n'est ni référencée ni gardée en mémoire par les caches.
useSeoMeta({ title: 'Mon contrat', robots: 'noindex' })
const route = useRoute()
const reference = computed(() => String(route.params.reference))
const cle = computed(() => (typeof route.query.cle === 'string' ? route.query.cle : ''))
</script>

<template>
  <section class="conteneur contrat-structure">
    <h1>Contrat {{ reference }}</h1>
    <p v-if="!cle" class="alerte alerte-erreur" role="alert">
      Ce lien est incomplet. Ouvrez-le depuis le SMS que nous vous avons envoyé, ou appelez-nous.
    </p>
    <FilContrat v-else class="carte bloc" :base="`/api/v1/contrat/${reference}`" :requete="{ cle }" />
  </section>
</template>

<style scoped>
.contrat-structure { padding-top: 24px; max-width: 720px; }
.bloc { padding: 16px; }
</style>
