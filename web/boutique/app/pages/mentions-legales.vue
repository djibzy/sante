<script setup lang="ts">
useSeoMeta({ title: 'Mentions légales', robots: 'noindex' })
const config = useRuntimeConfig()
const whatsapp = computed(() => (config.public.whatsapp ? `+${config.public.whatsapp}` : null))
</script>

<template>
  <PageJuridique titre="Mentions légales" mise-a-jour="13 novembre 2026">
    <h2>Éditeur</h2>
    <p>
      Bibou est une marque de Yasal Santé, [forme juridique et capital], dont le siège est à
      Bamako, [adresse]. RCCM : [à compléter]. NIF : [à compléter].
    </p>
    <p>Directeur de la publication : [nom et fonction].</p>
    <p>
      Contact : <template v-if="whatsapp">WhatsApp {{ formaterTelephone(whatsapp) }}, </template>[adresse de courriel].
    </p>

    <h2>Hébergement</h2>
    <p>[Nom de l'hébergeur, adresse, pays].</p>

    <h2>Propriété intellectuelle</h2>
    <p>
      Les marques Bibou et Yasal Santé, les logos, les textes et les photos du site appartiennent
      à Yasal Santé. Toute reproduction demande son accord écrit.
    </p>

    <h2>Données personnelles</h2>
    <p>
      Voir la <NuxtLink to="/confidentialite">politique de confidentialité</NuxtLink>. Le
      traitement des données des clients est déclaré à l'Autorité de protection des données à
      caractère personnel (APDP) : [numéro de récépissé à compléter].
    </p>
  </PageJuridique>
</template>
