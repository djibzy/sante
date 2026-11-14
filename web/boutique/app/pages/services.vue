<script setup lang="ts">
useSeoMeta({ title: 'Nos autres services', description: 'Kits de soins, matériel médical, campagnes de sensibilisation, devis pour les structures de santé.' })
const SERVICES = [
  { id: 'couleurs', titre: 'Votre structure à vos couleurs', texte: 'Déposez votre logo : votre palette, la peinture RAL la plus proche pour vos murs, et votre équipe habillée à vos couleurs, logo brodé. Un seul interlocuteur, du logo à la blouse.', lien: '/a-vos-couleurs', action: 'Essayer avec votre logo', picto: 'blouses-medicales' },
  { id: 'kits', titre: 'Kits de soins', texte: "Kits d'hygiène, de premiers secours et du relais communautaire, composés article par article et assemblés à l'atelier.", lien: '/rayons/kits', action: 'Voir les kits', picto: 'kits' },
  { id: 'materiel', titre: 'Matériel médical', texte: 'Thermomètres et tensiomètres. Les articles du domaine pharmaceutique sont délivrés par notre pharmacien partenaire.', lien: '/rayons/materiel-medical', action: 'Voir le matériel', picto: 'materiel-medical' },
  { id: 'campagnes', titre: 'Campagnes de sensibilisation', texte: 'T-shirts et casquettes imprimés, affiches et boîtes à images conçues avec notre studio et relues par notre comité médical.', lien: '/rayons/campagnes', action: 'Préparer une campagne', picto: 'campagnes' },
  { id: 'structures', titre: 'Devis pour les structures', texte: "CSCom, cliniques, pharmacies, écoles de santé, ONG : la tenue de toute l'équipe, un nom brodé par personne, puis un devis PDF avec votre logo et le prix professionnel, à accepter en ligne.", lien: '/commande-equipe', action: 'Commander pour une équipe', picto: 'blouses-medicales' },
]
</script>

<template>
  <section class="conteneur services">
    <EnteteListe titre="Nos autres services" description="Au-delà des tenues, Bibou équipe les soignants et les structures, et accompagne leurs campagnes." />
    <div class="grille">
      <article v-for="s in SERVICES" :id="s.id" :key="s.id" class="carte service">
        <ChartePictogramme :type="s.picto" :taille="56" />
        <h2>{{ s.titre }}</h2>
        <p>{{ s.texte }}</p>
        <NuxtLink :to="s.lien" class="bouton bouton-secondaire">{{ s.action }}</NuxtLink>
      </article>
    </div>
    <div class="carte bientot">
      <h2>Bientôt chez Yasal Santé</h2>
      <p>La formation continue des soignants et le studio de communication santé rejoignent la même maison, avec le même compte.</p>
    </div>
  </section>
</template>

<style scoped>
.services { display: grid; gap: 20px; }
.grille { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); }
.service { padding: 20px; display: grid; gap: 10px; align-content: start; justify-items: start; scroll-margin-top: 140px; }
.service h2 { margin: 4px 0 0; font-size: 1.2rem; }
.service p { margin: 0; color: var(--texte-doux); }
.bientot { padding: 20px; background: var(--fond-doux); border-style: dashed; }
.bientot h2 { margin-top: 0; font-size: 1.1rem; }
.bientot p { margin: 0; }
</style>
