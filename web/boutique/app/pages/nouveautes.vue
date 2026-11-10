<script setup lang="ts">
useSeoMeta({ title: 'Nouveautés' })
</script>

<template>
  <section class="conteneur">
    <EnteteListe titre="Nouveautés" description="Les dernières tenues sorties de l'atelier : nouvelles coupes, nouvelles couleurs, la collection wax." />
    <ListeProduits :cadre="{ nouveau: true }" />
  </section>
</template>
