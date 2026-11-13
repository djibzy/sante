<script setup lang="ts">
// « Quelle taille choisir ? » : la taille conseillée d'après ses mesures, choisie d'un geste.
const props = defineProps<{ pointure?: boolean, disponibles?: string[], informatif?: boolean }>()
const emit = defineEmits<{ choisir: [taille: string] }>()
const mesures = reactive<{ poitrine: number | null, tour: number | null, hanches: number | null, pied: number | null }>({
  poitrine: null, tour: null, hanches: null, pied: null,
})
const conseil = computed(() => (props.pointure ? pointureConseillee(mesures.pied) : tailleConseillee(mesures)))
const disponible = (taille: string) => !props.disponibles || props.disponibles.includes(taille)
</script>

<template>
  <details class="trouver-taille">
    <summary>{{ pointure ? 'Quelle pointure choisir ?' : 'Quelle taille choisir ?' }}</summary>
    <p class="aide">Mesurez-vous avec un mètre ruban, sans serrer. <NuxtLink to="/guide-des-tailles">Comment se mesurer</NuxtLink></p>
    <div class="mesures">
      <template v-if="pointure">
        <label class="champ"><span>Longueur du pied (cm)</span><input v-model.number="mesures.pied" type="number" inputmode="decimal" min="15" max="35" step="0.1"></label>
      </template>
      <template v-else>
        <label class="champ"><span>Tour de poitrine (cm)</span><input v-model.number="mesures.poitrine" type="number" inputmode="numeric" min="60" max="160"></label>
        <label class="champ"><span>Tour de taille (cm)</span><input v-model.number="mesures.tour" type="number" inputmode="numeric" min="50" max="160"></label>
        <label class="champ"><span>Tour de hanches (cm)</span><input v-model.number="mesures.hanches" type="number" inputmode="numeric" min="60" max="170"></label>
      </template>
    </div>
    <div v-if="conseil" class="conseil" role="status">
      <p v-if="conseil.horsGuide">
        Vos mesures dépassent notre guide : écrivez-nous, nous vous conseillons (et pouvons fabriquer sur mesure).
      </p>
      <template v-else>
        <p>
          {{ pointure ? 'Pointure conseillée' : 'Taille conseillée' }} : <strong>{{ conseil.taille }}</strong>
          <template v-if="conseil.ou">, ou <strong>{{ conseil.ou }}</strong> pour plus d'aisance (coupe cintrée)</template>
        </p>
        <div v-if="!informatif" class="choix">
          <button v-if="disponible(conseil.taille)" type="button" class="bouton bouton-secondaire" @click="emit('choisir', conseil.taille)">Choisir {{ conseil.taille }}</button>
          <button v-if="conseil.ou && disponible(conseil.ou)" type="button" class="bouton bouton-discret" @click="emit('choisir', conseil.ou!)">Choisir {{ conseil.ou }}</button>
          <span v-if="!disponible(conseil.taille)" class="aide">Cette taille n'existe pas pour cet article : écrivez-nous.</span>
        </div>
      </template>
    </div>
  </details>
</template>

<style scoped>
.trouver-taille { margin: 4px 0 14px; padding: 10px 12px; border: 1px solid var(--bordure); border-radius: 12px; background: var(--fond-doux); }
.trouver-taille summary { cursor: pointer; font-weight: 650; }
.trouver-taille p { margin: 8px 0 0; }
.mesures { display: grid; gap: 0 10px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 140px), 1fr)); margin-top: 8px; }
.mesures .champ { margin-bottom: 0.5rem; }
.mesures span { font-size: 0.85rem; font-weight: 600; }
.mesures input { width: 100%; }
.conseil { margin-top: 4px; }
.choix { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
</style>
