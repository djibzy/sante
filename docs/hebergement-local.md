# Héberger Bibou chez soi pour les essais réels

But : faire essayer Bibou et Prestations à de vraies personnes avant l'ouverture, depuis un
ordinateur à vous (ou un petit serveur), sans louer de serveur.

## Ce qu'il faut

- Un ordinateur qui reste allumé et connecté (Linux conseillé ; Windows ou Mac avec Docker
  Desktop marchent aussi), 4 Go de mémoire au moins, et **Docker**.
- Un onduleur ou une prise protégée si l'électricité est instable : une coupure en pleine
  écriture est le principal risque pour la base.
- Un nom de domaine (quelques milliers de FCFA par an) : sans lui, pas de HTTPS, et sans HTTPS
  le téléphone refuse d'installer l'application et d'enregistrer le catalogue hors ligne.

## Mettre en ligne depuis chez soi (sans toucher au routeur)

Les box et les forfaits mobiles n'ont pas d'adresse fixe et bloquent souvent les connexions
entrantes. La solution la plus simple est un **tunnel** : un petit programme sur votre ordinateur
ouvre une liaison sortante vers un service qui présente votre site sur Internet en HTTPS
(Cloudflare Tunnel, gratuit pour cet usage, demande un domaine géré chez eux). Les visiteurs vont
sur `boutique.votre-domaine.ml`, le tunnel amène la demande à votre ordinateur.

1. Cloner le dépôt, `cd infra && cp .env.example .env`, puis remplir `.env`
   (`DOMAINE=votre-domaine.ml`, mots de passe, clés : `uv run python -m comptes.outils generer-cles`).
2. `docker compose up -d --build`.
3. Créer les comptes de l'équipe (README, « Créer l'équipe »).
4. Installer le tunnel et lui indiquer les trois adresses (`comptes.`, `boutique.`,
   `prestations.`) vers le port 80 de l'ordinateur. Suivre la documentation du fournisseur du
   tunnel : ses écrans changent.
5. Sur un téléphone, ouvrir `https://boutique.votre-domaine.ml`.

Variante pour une toute première démonstration, sans domaine : même réseau Wi-Fi, adresse
`http://<adresse de l'ordinateur>:3000`. Le site s'affiche, mais pas l'installation de
l'application ni le mode hors ligne.

## Avant de faire essayer de vraies personnes

- Réglages d'essai : `BOUTIQUE_PAIEMENT_MOBILE=aucun` (le client paie à la livraison, CinetPay
  n'est pas nécessaire pour le pilote), `SMS_FOURNISSEUR=journal` tant que le compte SMS n'est
  pas ouvert (aucun SMS ne part : les messages restent dans la boîte d'envoi).
- Les textes « Conditions de vente », « Confidentialité » et « Mentions légales » sont des
  projets : les faire relire avant d'inviter des inconnus, puis `TEXTES_JURIDIQUES_VALIDES=true`.
- Dès qu'un vrai client laisse son nom et son numéro, ce sont des données personnelles : limiter
  l'essai à des proches ou à des clients prévenus, et vérifier la déclaration à l'APDP.
- **Sauvegardes** : `infra/sauvegarde.sh` (chaque nuit) et une copie sur un disque ou un cloud
  qui n'est pas l'ordinateur. Essayer une restauration (`infra/essai-restauration.sh`).
- **Surveillance** : le service d'alerte par SMS (docs/exploitation.md) doit tourner sur une
  autre machine que celle qui héberge.

  ordinateur. Rien du code ne change.
- Passer à un hébergeur quand l'essai devient une vraie ouverture : même procédure, un autre
  ordinateur. Aucune ligne de code ne change.
