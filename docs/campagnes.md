# Campagnes : concevoir, mobiliser et évaluer une campagne de sensibilisation

Produit à part (service `campagnes`, base `campagnes`, port 8004, sous-domaine `campagnes.`),
sur le socle commun. **Pas prévu pour le lancement de Bibou** : il se construit ensuite, par
phases, à partir de l'import du fondateur (à analyser avant de coder). Décision D29.

## Pour qui

| Acteur | Ce qu'il fait |
|---|---|
| **Structure organisatrice** (association, ONG, clinique, centre de santé, collectivité) | Monte une campagne, recrute ses bénévoles, trouve des partenaires, suit et évalue |
| **Bénévole** | Trouve une campagne près de lui, s'inscrit, reçoit des missions, rapporte son activité, reçoit une attestation |
| **Partenaire** (financier, en nature, compétence, média, lieu) | Cherche des campagnes à soutenir, propose son soutien, suit l'usage de ce qu'il a donné |
| **Référent santé** (nommé par la structure) | Valide les messages de santé avant diffusion |
| **Équipe de la plateforme** | Vérifie les structures avant publication, modère |
| **Public** | Voit les campagnes ouvertes et leurs résultats agrégés |

## Les normes sur lesquelles on s'appuie

- **Cycle d'une campagne : le P-Process** (Johns Hopkins CCP / Compass for SBC), cinq étapes :
  *Enquêter* (situation, audiences, obstacles), *Concevoir la stratégie* (objectifs mesurables,
  théorie du changement, canaux, suivi-évaluation), *Créer et tester* (supports prétestés auprès de
  l'audience), *Mobiliser et suivre* (rôles des partenaires, formation, suivi, corrections en
  route), *Évaluer et faire évoluer* (résultats, diffusion même si mitigés, suites). Transversal :
  une théorie du changement de comportement, la participation des parties prenantes, le renforcement
  continu des capacités. Le produit suit ces cinq étapes comme les étapes d'une campagne.
- **Évaluation : modèle logique de l'OMS** : intrants, activités, extrants, résultats (changement
  de connaissances, d'attitudes, de comportements), impact (santé à long terme, difficile à
  attribuer à une seule campagne). Trois moments : initial (référence), mi-parcours, final. Le suivi
  est prévu dès la conception. Six principes des supports : accessibles, pertinents, actionnables,
  opportuns, crédibles, compréhensibles.
- **Bénévoles : cycle de gestion de la Fédération internationale de la Croix-Rouge (IFRC)** :
  recrutement planifié (tâches, nombre, rôles, compétences), accueil (entretien, références,
  dossier), mission (manuel, formation, accompagnement), suivi (autoévaluation, débriefing),
  reconnaissance (attestation, remerciements, remboursement des frais), départ (réorientation,
  confidentialité). Sécurité : code de conduite, non-discrimination, assurance à connaître,
  incidents documentés sans interprétation, charge de travail réaliste.
- **Associations au Mali** : la loi n° 04-038 du 5 août 2004. Une association n'a la capacité
  juridique qu'après déclaration (récépissé), avec publication au Journal officiel dans les trois
  mois ; les associations étrangères ou humanitaires ont un régime à part. La plateforme demande le
  récépissé et le fait vérifier avant de publier une structure.
- **Données personnelles** : loi n° 2013-015 et APDP (déclaration avant collecte). Les nom,
  téléphone et disponibilités des bénévoles sont des données personnelles ; à déclarer.

À vérifier avant le lancement par un juriste : le texte complet de la loi 2013-015 (je n'ai lu que
des résumés), l'assurance des bénévoles, le cadre applicable aux campagnes menées avec les
services de l'État (direction régionale de la santé, ministère).

## Le parcours d'une campagne

1. **Enquêter** : problème, zone, audiences, obstacles, situation de départ (indicateurs de référence).
2. **Concevoir** : objectifs mesurables (SMART), théorie du changement, **cadre logique**
   (intrants, activités, extrants, résultats, impact avec indicateurs, valeur de départ, cible),
   canaux, calendrier, budget, risques, besoins en bénévoles et en soutiens.
3. **Créer et tester** : messages et supports (langues du public), prétest auprès de l'audience,
   **validation du référent santé** avant tout usage public.
4. **Mobiliser et suivre** : appel aux bénévoles, missions, appel aux partenaires, rapports
   d'activité du terrain, corrections.
5. **Évaluer et faire évoluer** : bilan à mi-parcours et final, rapport (PDF), leçons, suite.

## Les modules

1. **Fiche de campagne et cadre logique** : l'étape en cours, les indicateurs (référence, cible,
   réalisé), les pièces jointes.
2. **Bénévoles** : appel (profil, tâches, nombre, lieu, dates), inscription, entretien, sélection,
   acceptation de la charte et du code de conduite, formation suivie, missions, présence, débriefing,
   attestation PDF, départ. Règles : mineurs avec accord du parent ; jamais seul avec des enfants ;
   frais remboursés notés ; un bénévole peut quitter à tout moment.
3. **Missions et terrain** : mission = lieu, créneau, effectif, chef d'équipe. Rapport d'activité
   sur téléphone, **hors ligne** (comme la tournée de Prestations) : personnes touchées en nombres
   (tranche d'âge, sexe), matériels distribués, incidents, photos avec consentement.
4. **Partenaires** : profil (type de soutien, domaines, zones), **besoins chiffrés** de chaque
   campagne (50 000 FCFA, 200 affiches, un véhicule, un animateur), recherche dans les deux sens
   (la structure trouve des partenaires, le partenaire trouve des campagnes à soutenir), proposition
   → accord daté de la structure (comme les propositions de Bibou) → suivi des engagements tenus →
   remerciement et compte rendu d'usage.
5. **Suivi-évaluation** : tableau de bord par campagne et par indicateur, comparaison à la cible,
   alertes (retard, mission sans effectif), rapports mi-parcours et final, export CSV.
6. **Messagerie** : le fil sécurisé de Bibou (D26), par campagne, mission et partenariat.
7. **Médiathèque de messages** : messages validés, par langue, réutilisables par d'autres structures.
8. **Vérification et modération** : structure vérifiée (récépissé), campagne relue avant
   publication, signalement.

## Règles du produit

- **Aucune donnée de santé individuelle.** La campagne sensibilise ; elle ne dit rien de la santé
  d'une personne. Les chiffres du terrain sont **agrégés** ; un comptage trop petit pour une zone
  est regroupé. (Règle du dépôt : les données de santé relèvent du futur service d'orientation
  médicale.)
- **Messages de santé validés** par un référent nommé, qui en porte la responsabilité, avant diffusion.
- **La plateforme ne touche pas à l'argent** au départ : les soutiens financiers sont des engagements
  déclarés et suivis, versés directement à la structure. Collecte de dons en ligne : plus tard, après
  avis juridique.
- **Données des bénévoles** : le strict nécessaire, déclarées à l'APDP, effacées à la fin d'une durée
  fixée, exportables, supprimables ; les contacts ne sont jamais montrés aux partenaires.
- Un message jamais modifié, un retrait motivé et journalisé ; toute écriture sensible journalisée
  (règles du dépôt).

## Phases

| Phase | Contenu | Quand |
|---|---|---|
| 0 | Analyse de l'import du fondateur, vocabulaire, écrans à dessiner | avant tout code |
| 1 | Structures vérifiées, campagnes avec cadre logique, appel aux bénévoles, missions, présence, attestation | premier lot |
| 2 | Partenaires, besoins chiffrés, propositions et accords, tableau de bord | deuxième lot |
| 3 | Rapports de terrain hors ligne, suivi-évaluation complet, rapports PDF, messagerie, médiathèque | troisième lot |
| 4 | Dons en ligne, données ouvertes agrégées, réseau de structures | après avis juridique |

## Décisions prises (15 novembre 2026, par délégation du fondateur ; réversibles)

1. **Organisateur : Yasal Santé seule pour le test de décembre 2026.** Le modèle de données est
   dès le départ multi-structures, mais l'inscription reste fermée (structures ajoutées par
   l'équipe, sur invitation). L'ouverture à d'autres structures vient après le test, une fois la
   vérification rodée.
2. **Vérification et relecture : l'équipe de la plateforme** (rôle `campagnes:admin`). Elle vérifie
   le récépissé d'une structure avant qu'elle ne publie, et relit chaque campagne avant sa
   publication. Pour le test, c'est le fondateur.
3. **Référent santé : un professionnel de santé nommé par la structure**, enregistré dans la
   campagne (nom, fonction, date de validation de chaque message). Un message de santé sans
   validation datée ne peut pas être publié. **À désigner par le fondateur** : c'est une personne
   réelle et responsable, je ne peux pas la choisir.
4. **Langues : français et bambara** pour les supports, une langue par support, l'interface en
   français. D'autres langues (soninké, peul, songhaï, tamasheq…) s'ajoutent support par support.

## Modèle économique (hypothèses à tester, aucun chiffre validé)

Principe : les structures qui font de la sensibilisation ont peu d'argent ; le produit ne doit pas
les taxer au départ. Il vit de ce qui l'entoure et de ceux qui ont intérêt à soutenir.

| Source | Principe | Quand | Réserve |
|---|---|---|---|
| **Services de l'écosystème** | Chaque campagne a besoin de supports (Studio), de bénévoles formés (Formation), de tenues et de kits (Bibou). La plateforme les propose au bon moment du parcours | dès le test | C'est le débouché le plus naturel : les trois produits existent déjà ou sont prévus |
| **Forfaits pour partenaires et entreprises** | Visibilité et compte rendu d'impact pour les entreprises qui soutiennent (responsabilité sociétale) : mention, rapport dédié, événement | après le test | Ne pas vendre l'indépendance de la campagne : le message de santé n'est jamais influencé par le soutien |
| **Abonnement des structures** | Gratuit pour les petites associations ; payant pour les grandes (ONG, institutions) qui ont besoin de plusieurs campagnes, d'équipes, de rapports et d'exports | phase 2 ou 3 | À tester : le seuil gratuit/payant se fixe avec de vrais usages |
| **Subventions et programmes** | Financement de la plateforme comme outil d'intérêt général (déjà dans le plan financier) | en continu | Dépend des bailleurs et de leurs calendriers |
| **Commission sur les dons** | Part prélevée sur des dons collectés en ligne | phase 4 seulement | Exige de manier l'argent : avis juridique et agrément de paiement d'abord ; écartée tant que la plateforme ne touche pas à l'argent |

À mesurer pendant le test de décembre pour fixer les prix : le temps gagné par la structure, le
nombre de bénévoles réellement mobilisés, les soutiens obtenus, ce qu'elle serait prête à payer et
pour quoi. Les prix et les seuils se décident avec ces chiffres, pas avant.

## Reste à préciser avec le fondateur

- Le sujet et les dates de la campagne de décembre 2026 (l'outil se règle sur elle).
- Le nom du référent santé.
- Le contenu de l'import : ce qui est repris tel quel, ce qui est reconstruit.
