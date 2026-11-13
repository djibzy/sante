"""Catalogue (rayons, produits, variantes, images), zones de livraison, commandes et devis.

Règle réglementaire (décret n° 04-557) : chaque produit porte une catégorie. Les articles du
domaine pharmaceutique ne sont pas vendus en ligne par la boutique ; ils passent par le
pharmacien partenaire.

Montants en FCFA, en entiers. Une commande ne contient aucune donnée de santé.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from boutique.atelier.etats import EtatOrdre, MotifStock
from boutique.commandes.cycle import ModeLivraison, Moyen, Statut, valeurs_sql
from boutique.metiers import GENRES, MANCHES, UNIVERS
from socle.audit import JournalAuditMixin
from socle.db import CONVENTION_NOMMAGE, HorodatageMixin, IdMixin

CATEGORIE_LIBRE = "libre"
CATEGORIE_PHARMACEUTIQUE = "pharmaceutique"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENTION_NOMMAGE)


def _valeurs(cles: dict[str, str]) -> str:
    return ", ".join(f"'{cle}'" for cle in cles)


class PosteAtelier(IdMixin, HorodatageMixin, Base):
    """Poste de l'atelier et sa capacité, qui sert à calculer les dates promises."""

    __tablename__ = "postes_atelier"
    __table_args__ = (CheckConstraint("capacite_jour > 0", name="capacite_positive"),)

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    capacite_jour: Mapped[int] = mapped_column(nullable=False)  # pièces par jour ouvré
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


class Rayon(IdMixin, HorodatageMixin, Base):
    __tablename__ = "rayons"
    __table_args__ = (CheckConstraint(f"univers IN ({_valeurs(UNIVERS)})", name="univers_valide"),)

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # Famille du menu : tenues médicales, kits et matériel, campagnes.
    univers: Mapped[str] = mapped_column(
        String(20), nullable=False, default="tenues", server_default="tenues"
    )
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


class Produit(IdMixin, HorodatageMixin, Base):
    __tablename__ = "produits"
    __table_args__ = (
        CheckConstraint(
            f"categorie_reglementaire IN ('{CATEGORIE_LIBRE}', '{CATEGORIE_PHARMACEUTIQUE}')",
            name="categorie_valide",
        ),
        CheckConstraint(
            f"categorie_reglementaire <> '{CATEGORIE_LIBRE}' OR prix_public IS NOT NULL",
            name="prix_requis",
        ),
        CheckConstraint("prix_public IS NULL OR prix_public >= 0", name="prix_positif"),
        CheckConstraint(
            "prix_avant_promo IS NULL OR prix_avant_promo > prix_public", name="promo_coherente"
        ),
        CheckConstraint(f"genre IS NULL OR genre IN ({_valeurs(GENRES)})", name="genre_valide"),
        CheckConstraint(
            f"manches IS NULL OR manches IN ({_valeurs(MANCHES)})", name="manches_valides"
        ),
        CheckConstraint(
            "nombre_avis >= 0 AND somme_notes BETWEEN nombre_avis AND 5 * nombre_avis",
            name="avis_coherents",
        ),
        Index("ix_produits_metiers", "metiers", postgresql_using="gin"),
    )

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    resume: Mapped[str] = mapped_column(String(300), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    rayon_id: Mapped[UUID] = mapped_column(ForeignKey("rayons.id"), index=True, nullable=False)
    categorie_reglementaire: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CATEGORIE_LIBRE, server_default=CATEGORIE_LIBRE
    )
    personnalisable: Mapped[bool] = mapped_column(nullable=False, default=False)
    prix_public: Mapped[int | None] = mapped_column()  # en FCFA, hors taxes
    prix_pro: Mapped[int | None] = mapped_column()  # prix professionnel, si différent
    delai_jours: Mapped[int] = mapped_column(nullable=False, default=7, server_default="7")
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())
    # Poste de l'atelier qui fabrique l'article (broderie, impression, assemblage) ; vide pour
    # un article vendu tel quel, suivi en stock.
    poste_atelier: Mapped[str | None] = mapped_column(ForeignKey("postes_atelier.code"))
    seuil_alerte: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    # Pour ranger et filtrer comme une boutique de tenues médicales : par métier, genre, manches.
    metiers: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list, server_default="{}"
    )
    genre: Mapped[str | None] = mapped_column(String(10))
    manches: Mapped[str | None] = mapped_column(String(10))
    collection: Mapped[str | None] = mapped_column(String(60))
    matiere: Mapped[str] = mapped_column(String(200), nullable=False, default="", server_default="")
    entretien: Mapped[str] = mapped_column(
        String(300), nullable=False, default="", server_default=""
    )
    est_nouveau: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=false())
    prix_avant_promo: Mapped[int | None] = mapped_column()  # prix barré pendant une promotion
    # Avis publiés, recomptés à chaque décision de l'équipe : les listes affichent la note
    # sans calcul. Moyenne = somme_notes / nombre_avis.
    nombre_avis: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    somme_notes: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    rayon: Mapped[Rayon] = relationship(lazy="raise")
    variantes: Mapped[list["Variante"]] = relationship(
        back_populates="produit",
        cascade="all, delete-orphan",
        order_by="Variante.position",
        lazy="raise",
    )
    images: Mapped[list["ImageProduit"]] = relationship(
        cascade="all, delete-orphan", order_by="ImageProduit.position", lazy="raise"
    )

    @property
    def vendable_en_ligne(self) -> bool:
        return self.categorie_reglementaire == CATEGORIE_LIBRE


class Variante(IdMixin, Base):
    __tablename__ = "variantes"
    __table_args__ = (
        CheckConstraint("couleur_hex IS NULL OR couleur_hex ~ '^#[0-9a-f]{6}$'", name="hex_valide"),
    )

    produit_id: Mapped[UUID] = mapped_column(
        ForeignKey("produits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    couleur_hex: Mapped[str | None] = mapped_column(String(7))  # pastille, ex. #1f4fa8
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    taille: Mapped[str | None] = mapped_column(String(20))
    couleur: Mapped[str | None] = mapped_column(String(40))
    prix: Mapped[int | None] = mapped_column()  # remplace le prix public du produit si renseigné
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    produit: Mapped[Produit] = relationship(back_populates="variantes", lazy="raise")


class ImageProduit(IdMixin, Base):
    __tablename__ = "images_produits"

    produit_id: Mapped[UUID] = mapped_column(
        ForeignKey("produits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    texte_alternatif: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")


class ZoneLivraison(IdMixin, HorodatageMixin, Base):
    __tablename__ = "zones_livraison"
    __table_args__ = (
        CheckConstraint("frais >= 0", name="frais_positifs"),
        CheckConstraint("delai_jours >= 0", name="delai_positif"),
    )

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    frais: Mapped[int] = mapped_column(nullable=False)
    delai_jours: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    est_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


def _maintenant() -> datetime:
    # Heure de l'application et non de la transaction : deux événements écrits dans la même
    # transaction gardent leur ordre.
    return datetime.now(UTC)


class Livreur(IdMixin, HorodatageMixin, Base):
    """Livreur de la boutique (salarié ou coursier à moto)."""

    __tablename__ = "livreurs"

    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164
    est_actif: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())


class Commande(IdMixin, HorodatageMixin, Base):
    """Commande d'un client, ou devis demandé par une structure qui devient commande s'il est
    accepté. Le numéro (référence BB-1001) est attribué par la base."""

    __tablename__ = "commandes"
    __table_args__ = (
        CheckConstraint(f"statut IN ({valeurs_sql(Statut)})", name="statut_valide"),
        CheckConstraint(
            f"mode_livraison IN ({valeurs_sql(ModeLivraison)})", name="mode_livraison_valide"
        ),
        CheckConstraint(
            f"mode_livraison = '{ModeLivraison.RETRAIT}' OR zone_id IS NOT NULL",
            name="zone_requise",
        ),
        CheckConstraint(
            "sous_total >= 0 AND frais_livraison >= 0 AND remise >= 0 AND montant_paye >= 0",
            name="montants_positifs",
        ),
        CheckConstraint("total = sous_total + frais_livraison - remise", name="total_coherent"),
        CheckConstraint("total >= 0", name="total_positif"),
        CheckConstraint("acompte >= 0 AND acompte <= total", name="acompte_valide"),
        CheckConstraint(
            "acompte_garde >= 0 AND acompte_garde <= acompte", name="acompte_garde_valide"
        ),
    )

    numero: Mapped[int] = mapped_column(Integer, Identity(start=1001), unique=True, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    client_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)  # compte unique, si connecté
    nom_client: Mapped[str] = mapped_column(String(120), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # E.164
    email: Mapped[str | None] = mapped_column(String(200))
    etablissement: Mapped[str | None] = mapped_column(String(160))
    mode_livraison: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[UUID | None] = mapped_column(ForeignKey("zones_livraison.id"))
    adresse: Mapped[str] = mapped_column(String(300), nullable=False, default="", server_default="")
    note_client: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    mode_paiement: Mapped[str] = mapped_column(String(30), nullable=False)
    sous_total: Mapped[int] = mapped_column(nullable=False)
    frais_livraison: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    remise: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    total: Mapped[int] = mapped_column(nullable=False)
    montant_paye: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    # Acompte des articles faits à la demande, fixé à la commande (ou au devis) : il lance la
    # fabrication et reste acquis si le client annule ensuite.
    acompte: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    # Part de l'acompte gardée quand le client annule (non remboursable) ; le reste lui est rendu.
    acompte_garde: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    date_promise: Mapped[date | None] = mapped_column(Date)
    devis_emis_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    devis_valable_jusqu_au: Mapped[date | None] = mapped_column(Date)
    # Empreinte SHA-256 de la clé du lien de suivi ; la clé elle-même n'est jamais stockée.
    empreinte_cle_suivi: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    livreur_id: Mapped[UUID | None] = mapped_column(ForeignKey("livreurs.id"), index=True)

    zone: Mapped[ZoneLivraison | None] = relationship(lazy="raise")
    livreur: Mapped["Livreur | None"] = relationship(lazy="raise")
    facture: Mapped["Facture | None"] = relationship(lazy="raise", back_populates="commande")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="LigneCommande.position",
        lazy="raise",
    )
    evenements: Mapped[list["EvenementCommande"]] = relationship(
        cascade="all, delete-orphan", order_by="EvenementCommande.cree_le", lazy="raise"
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        order_by="Paiement.encaisse_le", lazy="raise"
    )

    @property
    def reference(self) -> str:
        return f"BB-{self.numero}"

    @property
    def reste_a_payer(self) -> int:
        return max(self.total - self.montant_paye, 0)


class LigneCommande(IdMixin, Base):
    """Ligne figée au moment de la commande (libellé et prix), ou ligne libre d'un devis
    (forfait de broderie d'un logo, par exemple) sans produit associé."""

    __tablename__ = "lignes_commande"
    __table_args__ = (
        CheckConstraint("quantite > 0", name="quantite_positive"),
        CheckConstraint("prix_unitaire >= 0", name="prix_positif"),
        CheckConstraint("montant = quantite * prix_unitaire", name="montant_coherent"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    produit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("produits.id", ondelete="SET NULL"), index=True
    )
    variante_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("variantes.id", ondelete="SET NULL")
    )
    libelle: Mapped[str] = mapped_column(String(250), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(60))
    quantite: Mapped[int] = mapped_column(nullable=False)
    prix_unitaire: Mapped[int] = mapped_column(nullable=False)
    montant: Mapped[int] = mapped_column(nullable=False)
    personnalisation: Mapped[str | None] = mapped_column(String(200))  # texte à broder
    position: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    commande: Mapped[Commande] = relationship(back_populates="lignes", lazy="raise")


class EvenementCommande(IdMixin, Base):
    """Historique daté : chaque changement de statut, avec une note éventuelle."""

    __tablename__ = "evenements_commande"

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    statut: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    visible_client: Mapped[bool] = mapped_column(nullable=False, default=True)
    acteur_id: Mapped[UUID | None] = mapped_column(Uuid)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )


class Paiement(IdMixin, Base):
    """Encaissement enregistré par l'équipe (paiement à la livraison, acompte d'un devis)."""

    __tablename__ = "paiements"
    __table_args__ = (
        CheckConstraint("montant > 0", name="montant_positif"),
        CheckConstraint(f"moyen IN ({valeurs_sql(Moyen)})", name="moyen_valide"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id"), index=True, nullable=False
    )
    montant: Mapped[int] = mapped_column(nullable=False)
    moyen: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(80))  # n° de transaction, de chèque…
    encaisse_par: Mapped[UUID | None] = mapped_column(Uuid)
    encaisse_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )


class OrdreFabrication(IdMixin, HorodatageMixin, Base):
    """Une ligne de commande à fabriquer, créée quand la commande est confirmée."""

    __tablename__ = "ordres_fabrication"
    __table_args__ = (
        CheckConstraint(f"etat IN ({valeurs_sql(EtatOrdre)})", name="etat_valide"),
        CheckConstraint("quantite > 0", name="quantite_positive"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ligne_id: Mapped[UUID] = mapped_column(
        ForeignKey("lignes_commande.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    poste: Mapped[str] = mapped_column(ForeignKey("postes_atelier.code"), nullable=False)
    libelle: Mapped[str] = mapped_column(String(250), nullable=False)
    personnalisation: Mapped[str | None] = mapped_column(String(200))
    quantite: Mapped[int] = mapped_column(nullable=False)
    etat: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    date_promise: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    commence_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    termine_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    commande: Mapped[Commande] = relationship(lazy="raise")


class MouvementStock(IdMixin, Base):
    """Journal du stock : le niveau d'un article est la somme de ses mouvements."""

    __tablename__ = "mouvements_stock"
    __table_args__ = (
        CheckConstraint(f"motif IN ({valeurs_sql(MotifStock)})", name="motif_valide"),
        CheckConstraint("quantite <> 0", name="quantite_non_nulle"),
    )

    produit_id: Mapped[UUID] = mapped_column(ForeignKey("produits.id"), index=True, nullable=False)
    variante_id: Mapped[UUID | None] = mapped_column(ForeignKey("variantes.id"), index=True)
    quantite: Mapped[int] = mapped_column(nullable=False)  # positive en entrée, négative en sortie
    motif: Mapped[str] = mapped_column(String(20), nullable=False)
    commande_id: Mapped[UUID | None] = mapped_column(ForeignKey("commandes.id"), index=True)
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="", server_default="")
    acteur_id: Mapped[UUID | None] = mapped_column(Uuid)
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )


class CompteurFactures(Base):
    """Dernier numéro de facture attribué, par année : verrouillé à chaque facture, il donne
    une numérotation continue, sans trou ni doublon."""

    __tablename__ = "compteurs_factures"

    annee: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    dernier: Mapped[int] = mapped_column(nullable=False, default=0)


class Facture(IdMixin, Base):
    """Facture d'une commande, émise à la livraison (ou plus tôt, à la demande d'une structure).
    Les lignes et les montants sont ceux de la commande, figés depuis sa confirmation."""

    __tablename__ = "factures"
    __table_args__ = (UniqueConstraint("annee", "numero"),)

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id"), unique=True, nullable=False
    )
    annee: Mapped[int] = mapped_column(nullable=False)
    numero: Mapped[int] = mapped_column(nullable=False)
    montant: Mapped[int] = mapped_column(nullable=False)
    emise_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )
    emise_par: Mapped[UUID | None] = mapped_column(Uuid)

    commande: Mapped[Commande] = relationship(back_populates="facture", lazy="raise")

    @property
    def reference(self) -> str:
        return f"F{self.annee}-{self.numero:05d}"


class Notification(IdMixin, Base):
    """SMS à envoyer au client (boîte d'envoi) ; jamais de donnée de santé dans le texte."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("etat IN ('a_envoyer', 'envoyee', 'echec')", name="etat_valide"),
        CheckConstraint("canal IN ('sms')", name="canal_valide"),
    )

    commande_id: Mapped[UUID | None] = mapped_column(ForeignKey("commandes.id"), index=True)
    canal: Mapped[str] = mapped_column(String(10), nullable=False)
    destinataire: Mapped[str] = mapped_column(String(20), nullable=False)  # E.164
    message: Mapped[str] = mapped_column(Text, nullable=False)
    etat: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    tentatives: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    derniere_erreur: Mapped[str | None] = mapped_column(String(500))
    identifiant_fournisseur: Mapped[str | None] = mapped_column(String(200))
    prochain_essai: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_maintenant
    )
    envoyee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TransactionPaiement(IdMixin, HorodatageMixin, Base):
    """Paiement en ligne demandé à l'agrégateur (CinetPay). Son statut ne vient jamais de la
    notification reçue : il est toujours relu auprès de l'agrégateur."""

    __tablename__ = "transactions_paiement"
    __table_args__ = (
        CheckConstraint(
            "statut IN ('initiee', 'acceptee', 'refusee', 'anomalie')", name="statut_valide"
        ),
        CheckConstraint("montant > 0", name="montant_positif"),
    )

    commande_id: Mapped[UUID] = mapped_column(
        ForeignKey("commandes.id"), index=True, nullable=False
    )
    fournisseur: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    montant: Mapped[int] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    adresse_paiement: Mapped[str | None] = mapped_column(String(500))
    operateur: Mapped[str | None] = mapped_column(String(20))  # OM, MOOV…
    reference_operateur: Mapped[str | None] = mapped_column(String(80))
    paiement_id: Mapped[UUID | None] = mapped_column(ForeignKey("paiements.id"))


class Avis(IdMixin, HorodatageMixin, Base):
    """Avis d'un client sur un produit qu'il a reçu : un par produit et par commande, publié
    seulement après relecture par l'équipe (aucune information médicale, aucun nom complet)."""

    __tablename__ = "avis"
    __table_args__ = (
        CheckConstraint("note BETWEEN 1 AND 5", name="note_valide"),
        CheckConstraint("statut IN ('en_attente', 'publie', 'refuse')", name="statut_valide"),
        CheckConstraint("statut <> 'refuse' OR motif_refus IS NOT NULL", name="motif_requis"),
        UniqueConstraint("commande_id", "produit_id"),
    )

    produit_id: Mapped[UUID] = mapped_column(ForeignKey("produits.id"), index=True, nullable=False)
    commande_id: Mapped[UUID] = mapped_column(ForeignKey("commandes.id"), nullable=False)
    note: Mapped[int] = mapped_column(nullable=False)
    texte: Mapped[str] = mapped_column(String(1000), nullable=False)
    auteur: Mapped[str] = mapped_column(String(60), nullable=False)  # « Aminata T. »
    statut: Mapped[str] = mapped_column(
        String(10), index=True, nullable=False, default="en_attente"
    )
    motif_refus: Mapped[str | None] = mapped_column(String(200))  # montré au client
    reponse: Mapped[str | None] = mapped_column(String(1000))  # de la boutique, publiée avec
    modere_par: Mapped[UUID | None] = mapped_column(Uuid)
    modere_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JournalAudit(JournalAuditMixin, Base):
    __tablename__ = "journal_audit"
