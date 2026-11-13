<script setup lang="ts">
useSeoMeta({ title: 'Conditions de vente et d\'utilisation', description: 'Commandes, prix, paiement, acompte, livraison, retours et compte : les règles de la boutique Bibou.' })

// Taux d'acompte et validité des devis : les réglages de la boutique, pour que le texte les suive.
const { data: regles } = await useBoutiqueFetch<{ acompte_pourcent: number, validite_devis_jours: number }>(
  '/api/v1/conditions-de-vente',
)
const taux = computed(() => (regles.value ? `de ${regles.value.acompte_pourcent} % de leur prix` : 'dont le montant figure dans le panier'))
const avecAcompte = computed(() => !regles.value || regles.value.acompte_pourcent > 0)
</script>

<template>
  <PageJuridique titre="Conditions de vente et d'utilisation" mise-a-jour="13 novembre 2026">
    <p>
      Ces conditions s'appliquent aux commandes passées sur la boutique Bibou, éditée par Yasal
      Santé (voir les <NuxtLink to="/mentions-legales">mentions légales</NuxtLink>), et à
      l'utilisation du site.
    </p>

    <h2>1. Articles</h2>
    <p>
      Tenues médicales, souvent brodées à votre nom dans notre atelier de Bamako, kits, matériel
      et supports de campagne. Les photos et couleurs sont aussi fidèles que possible. Les
      articles du domaine pharmaceutique ne sont ni vendus ni affichés avec un prix en ligne :
      notre pharmacien partenaire les délivre.
    </p>

    <h2>2. Commande</h2>
    <p>
      Vous choisissez vos articles, puis le retrait à la boutique ou la livraison. Vous recevez
      un SMS avec votre lien de suivi, et nous vous appelons pour confirmer. La commande est
      ferme quand nous l'avons confirmée ; avant, et tant que l'acompte d'un article fait à la
      demande est attendu, vous pouvez l'annuler depuis votre lien de suivi. Pour une structure,
      la demande de devis donne lieu à un devis valable {{ regles?.validite_devis_jours ?? 30 }}
      jours ; l'accepter en ligne vaut commande.
    </p>

    <h2>3. Prix</h2>
    <p>
      Prix en francs CFA. Le prix retenu est celui recalculé au moment de la commande, frais de
      livraison de votre zone compris ; il figure dans le SMS de confirmation. Le prix
      professionnel s'applique aux soignants et structures dont le statut a été vérifié.
      [Régime de TVA à préciser.]
    </p>

    <h2>4. Paiement</h2>
    <p>
      À la livraison ou au retrait, en espèces, par Orange Money ou par Moov Money. Une fois la
      commande confirmée, vous pouvez aussi payer en ligne par Orange Money ou Moov Money, sur la
      page sécurisée de notre partenaire CinetPay. Les articles faits à la demande demandent un
      acompte avant leur fabrication (article 6). La facture est émise à la remise des articles.
    </p>

    <h2>5. Fabrication, délais, livraison</h2>
    <p>
      La date indiquée à la commande dépend de la charge de l'atelier et de la zone ; nous la
      confirmons par téléphone et vous prévenons par SMS à chaque étape importante. En cas d'absence à la
      livraison, nous convenons ensemble d'un nouveau passage ou d'un retrait à la boutique.
    </p>

    <h2 id="acompte">6. Articles faits à la demande et acompte</h2>
    <p>
      Les articles brodés, imprimés ou personnalisés sont fabriqués pour vous et ne se revendent
      pas. Nous vérifions avec vous l'orthographe du texte avant de broder ou d'imprimer. Ces
      articles ne sont ni repris ni échangés, sauf défaut ou erreur de notre part.
    </p>
    <template v-if="avecAcompte">
      <p>
        Pour ces articles, un acompte {{ taux }} (arrondi à la centaine de francs supérieure)
        est demandé une fois la commande confirmée par téléphone. Son montant figure dans le
        panier et dans le SMS de confirmation, et vous l'acceptez en commandant. La fabrication
        commence à sa réception ; la date de livraison ou de retrait est fixée à ce moment-là.
        L'acompte se règle en ligne (Orange Money, Moov Money) ou à la boutique, le reste à la
        livraison ou au retrait.
      </p>
      <p>
        L'acompte n'est pas remboursable : si vous annulez la commande, il reste acquis à Bibou,
        car il couvre le tissu, la broderie ou l'impression et le temps de l'atelier engagés pour
        vous. Ce que vous avez payé au-delà de l'acompte vous est rendu. Si l'annulation vient de
        nous (article impossible à fabriquer, délai que nous ne pouvons pas tenir), tout vous est
        rendu.
      </p>
    </template>

    <h2>7. Échanges, retours et défauts</h2>
    <p>
      [Proposition à valider] Un article non personnalisé, non porté et dans son emballage peut
      être échangé, ou donner lieu à un avoir, dans les 7 jours suivant sa remise. Un article
      défectueux, ou différent de la commande, est remplacé ou remboursé : prévenez-nous dès que
      possible, par WhatsApp, avec une photo.
    </p>

    <h2>8. Avis</h2>
    <p>
      Seuls les clients qui ont reçu un article peuvent le noter. Chaque avis est relu avant
      publication ; nous refusons ceux qui contiennent une information médicale, un nom complet,
      un numéro de téléphone ou des propos injurieux, et vous en donnons le motif.
    </p>

    <h2>9. Compte</h2>
    <p>
      Un compte par numéro de téléphone. Gardez votre mot de passe pour vous ; en cas d'oubli,
      un code vous est envoyé par SMS. Vous pouvez supprimer votre compte à tout moment depuis
      « Mon compte ». Vos données sont traitées comme l'explique notre
      <NuxtLink to="/confidentialite">politique de confidentialité</NuxtLink>.
    </p>

    <h2>10. Droit applicable et litiges</h2>
    <p>
      Ces conditions relèvent du droit malien. En cas de désaccord, écrivez-nous : nous
      cherchons d'abord une solution amiable. À défaut, les tribunaux de Bamako sont compétents.
    </p>
  </PageJuridique>
</template>
