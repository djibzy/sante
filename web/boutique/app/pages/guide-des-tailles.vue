<script setup lang="ts">
useSeoMeta({ title: 'Guide des tailles', description: 'Mesures en centimètres pour choisir la taille de sa blouse, de sa tunique, de son pantalon et de ses chaussures.' })
const config = useRuntimeConfig()
// Mêmes mesures que le calcul de la taille conseillée (utils/tailles.ts).
const fourchette = ([de, a]: [number, number]) => `${de} à ${a}`
const HAUTS = MESURES_HAUTS.map(m => [m.taille, fourchette(m.poitrine), fourchette(m.tour), fourchette(m.hanches)])
const LONGUEURS = POINTURES.map(([pointure, cm]) => [pointure, cm.toFixed(1).replace('.', ',')])
const whatsapp = computed(() => `https://wa.me/${config.public.whatsapp}?text=${encodeURIComponent('Bonjour, voici mes mesures pour choisir ma taille : ')}`)
</script>

<template>
  <section class="conteneur guide">
    <EnteteListe titre="Guide des tailles" description="Mesurez-vous avec un mètre ruban, sur un vêtement léger, sans serrer." />
    <div class="colonnes">
      <div>
        <TrouverTaille informatif open />
        <h2>Blouses, tuniques et pantalons</h2>
        <div class="defilement">
          <table>
            <caption class="visuellement-cache">Mesures du corps en centimètres</caption>
            <thead><tr><th scope="col">Taille</th><th scope="col">Tour de poitrine</th><th scope="col">Tour de taille</th><th scope="col">Tour de hanches</th></tr></thead>
            <tbody><tr v-for="l in HAUTS" :key="l[0]"><th scope="row">{{ l[0] }}</th><td v-for="(v, i) in l.slice(1)" :key="i">{{ v }}</td></tr></tbody>
          </table>
        </div>
        <p class="aide">Mesures du corps, en centimètres. Les coupes cintrées taillent plus près du corps : entre deux tailles, prenez la plus grande.</p>
        <h2>Chaussures</h2>
        <TrouverTaille pointure informatif />
        <div class="defilement">
          <table>
            <caption class="visuellement-cache">Longueur du pied en centimètres</caption>
            <thead><tr><th scope="col">Pointure</th><th scope="col">Longueur du pied</th></tr></thead>
            <tbody><tr v-for="l in LONGUEURS" :key="l[0]"><th scope="row">{{ l[0] }}</th><td>{{ l[1] }} cm</td></tr></tbody>
          </table>
        </div>
      </div>
      <aside class="carte conseils">
        <h2>Comment se mesurer</h2>
        <ol>
          <li><strong>Poitrine</strong> : à l'endroit le plus fort, sous les bras.</li>
          <li><strong>Taille</strong> : au creux de la taille, au-dessus du nombril.</li>
          <li><strong>Hanches</strong> : à l'endroit le plus fort, debout pieds joints.</li>
          <li><strong>Pied</strong> : du talon au bout du plus long orteil, en fin de journée.</li>
        </ol>
        <p>Un doute avant la broderie ? Envoyez-nous vos mesures, nous vous conseillons.</p>
        <a :href="whatsapp" target="_blank" rel="noopener" class="bouton bouton-large">Envoyer mes mesures sur WhatsApp</a>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.colonnes { display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr); } /* les tableaux défilent dans leur cadre */
@media (min-width: 900px) { .colonnes { grid-template-columns: minmax(0, 1fr) 340px; align-items: start; } }
.defilement { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; min-width: 420px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--bordure); }
thead th { font-size: 0.88rem; color: var(--texte-doux); }
tbody th { color: var(--primaire); font-weight: 800; }
.conseils { padding: 20px; display: grid; gap: 8px; }
.conseils h2 { margin: 0; font-size: 1.15rem; }
.conseils ol { margin: 0; padding-left: 1.2em; display: grid; gap: 6px; }
.conseils p { margin: 0; }
</style>
