<script setup lang="ts">
// Note de 1 à 5, au clavier (flèches) comme au doigt : cinq boutons radio dessinés en étoiles.
const note = defineModel<number>({ required: true })
defineProps<{ nom: string, legende: string }>()
const survol = ref(0)
const LIBELLES = ['Très déçu', 'Déçu', 'Correct', 'Bien', 'Excellent']
const ETOILE = 'M12 2.6l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.5l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z'
const affichee = computed(() => survol.value || note.value)
</script>

<template>
  <fieldset class="choix-note">
    <legend>{{ legende }}</legend>
    <div class="ligne">
      <div class="etoiles" @mouseleave="survol = 0">
        <label v-for="n in 5" :key="n" :class="{ allumee: n <= affichee }" @mouseenter="survol = n">
          <input v-model="note" type="radio" :name="nom" :value="n" class="visuellement-cache">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path :d="ETOILE" /></svg>
          <span class="visuellement-cache">{{ n }} sur 5, {{ LIBELLES[n - 1] }}</span>
        </label>
      </div>
      <span class="libelle" aria-hidden="true">{{ affichee ? LIBELLES[affichee - 1] : 'Choisissez une note' }}</span>
    </div>
  </fieldset>
</template>

<style scoped>
.choix-note { border: 0; padding: 0; margin: 0; }
.choix-note legend { font-weight: 650; margin-bottom: 4px; padding: 0; }
.ligne { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.etoiles { display: flex; }
.etoiles label { display: grid; place-items: center; width: 44px; height: 44px; cursor: pointer; border-radius: 8px; }
.etoiles svg { width: 32px; height: 32px; fill: var(--etoile-vide); transition: fill 0.1s; }
.etoiles label.allumee svg { fill: var(--etoile); }
.etoiles label:has(input:focus-visible) { outline: 3px solid var(--primaire); outline-offset: -2px; }
.libelle { color: var(--texte-doux); font-weight: 600; }
</style>
