<script setup lang="ts">
useSeoMeta({ title: 'Promotions' })
</script>

<template>
  <section class="conteneur">
    <EnteteListe titre="Promotions" description="Prix réduits, dans la limite des stocks et jusqu'à la date annoncée en boutique." />
    <ListeProduits :cadre="{ promo: true }" />
  </section>
</template>
