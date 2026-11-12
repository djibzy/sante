"""Gestion des commandes par l'équipe (rôle boutique:admin) : file des commandes, statuts,
encaissements, devis, zones de livraison."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from boutique.commandes import acces, factures, operations
from boutique.commandes.cycle import ModeLivraison, Statut, passage_autorise
from boutique.commandes.pdf import reponse_devis, reponse_facture
from boutique.commandes.schemas import (
    ArretLivraison,
    ChangementStatut,
    CommandeGestion,
    CreationLivreur,
    CreationZone,
    EmissionDevis,
    LigneDevis,
    LivreurVue,
    ModificationLivreur,
    ModificationZone,
    NouveauPaiement,
    PageCommandes,
    ZoneGestion,
)
from boutique.commandes.tarifs import (
    INDISPONIBLE,
    PHARMACIEN,
    VARIANTE_INDISPONIBLE,
    VARIANTE_REQUISE,
    aujourd_hui,
    charger_produits,
    frais_de_livraison,
    libelle,
    prix_catalogue,
)
from boutique.commandes.vues import vue_gestion, vue_resume
from boutique.config import ROLE_ADMIN_BOUTIQUE, ParametresBoutique
from boutique.models import (
    Commande,
    JournalAudit,
    LigneCommande,
    Livreur,
    Paiement,
    Produit,
    ZoneLivraison,
)
from socle.audit import journaliser
from socle.db import session_db
from socle.security import Principal, exiger_role

routeur = APIRouter(prefix="/api/v1/admin", tags=["gestion des commandes"])
equipe = exiger_role(ROLE_ADMIN_BOUTIQUE)
_409 = status.HTTP_409_CONFLICT
_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
DEVIS_MODIFIABLES = frozenset({Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE})
SANS_ENCAISSEMENT = frozenset(
    {Statut.DEVIS_DEMANDE, Statut.DEVIS_ENVOYE, Statut.DEVIS_REFUSE, Statut.ANNULEE}
)


def _parametres(request: Request) -> ParametresBoutique:
    parametres: ParametresBoutique = request.app.state.parametres
    return parametres


@routeur.get("/commandes", summary="File des commandes et des devis")
async def lister(
    statut: list[Statut] | None = Query(None, description="Un ou plusieurs statuts"),
    q: str | None = Query(None, max_length=100, description="Référence, nom, téléphone"),
    page: int = Query(1, ge=1),
    par_page: int = Query(30, ge=1, le=100),
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> PageCommandes:
    filtres: list[ColumnElement[bool]] = []
    if statut:
        filtres.append(Commande.statut.in_(statut))
    if q and q.strip():
        texte = q.strip()
        chiffres = "".join(c for c in texte if c.isdigit())
        conditions: list[ColumnElement[bool]] = [
            Commande.nom_client.ilike(f"%{texte}%"),
            Commande.etablissement.ilike(f"%{texte}%"),
        ]
        if chiffres:
            conditions.append(Commande.telephone.contains(chiffres[-8:]))
            if len(chiffres) <= 9:
                conditions.append(Commande.numero == int(chiffres))
        filtres.append(or_(*conditions))
    total = await session.scalar(select(func.count(Commande.id)).where(*filtres))
    requete = (
        acces.requete_resumes()
        .where(*filtres)
        .order_by(Commande.cree_le.desc())
        .offset((page - 1) * par_page)
        .limit(par_page)
    )
    return PageCommandes(
        elements=[vue_resume(c, zone, n) for c, zone, n in await session.execute(requete)],
        total=total or 0,
        page=page,
        par_page=par_page,
    )


@routeur.get("/commandes/{reference}", summary="Détail d'une commande")
async def detail(
    reference: str,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CommandeGestion:
    return vue_gestion(await acces.charger(session, reference))


@routeur.post("/commandes/{reference}/statut", summary="Faire avancer une commande")
async def changer_statut(
    reference: str,
    donnees: ChangementStatut,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CommandeGestion:
    commande = await acces.charger(session, reference)
    depart = Statut(commande.statut)
    arrivee = donnees.statut
    if arrivee == Statut.DEVIS_ENVOYE:
        raise HTTPException(_409, "Un devis s'envoie avec ses prix et sa durée de validité")
    if not passage_autorise(depart, arrivee):
        raise HTTPException(_409, f"Passage impossible de « {depart.value} » à « {arrivee.value} »")
    if arrivee == Statut.EN_LIVRAISON and commande.mode_livraison != ModeLivraison.LIVRAISON:
        raise HTTPException(_409, "Cette commande est à retirer à la boutique")
    if donnees.livreur_id is not None:
        livreur = await session.get(Livreur, donnees.livreur_id)
        if livreur is None or not livreur.est_actif:
            raise HTTPException(_422, "Livreur inconnu")
        commande.livreur = livreur
    if donnees.date_promise is not None:
        commande.date_promise = donnees.date_promise
    await operations.appliquer_statut(
        session, commande, arrivee, principal.id, donnees.note.strip(), donnees.visible_client
    )
    journaliser(
        session,
        JournalAudit,
        action="commande.statut",
        acteur_id=principal.id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"de": depart.value, "vers": arrivee.value},
    )
    await session.commit()
    return vue_gestion(await acces.charger(session, reference))


@routeur.post("/commandes/{reference}/paiements", summary="Enregistrer un encaissement")
async def encaisser(
    reference: str,
    donnees: NouveauPaiement,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CommandeGestion:
    commande = await acces.charger(session, reference)
    await acces.verrouiller(session, commande.id)
    commande = await acces.charger(session, reference)  # montant payé à jour, sous verrou
    if Statut(commande.statut) in SANS_ENCAISSEMENT:
        raise HTTPException(_409, "Seule une commande confirmée peut être encaissée")
    if donnees.montant > commande.reste_a_payer:
        reste = f"{commande.reste_a_payer:,}".replace(",", " ")
        raise HTTPException(_422, f"Le montant dépasse le reste à payer ({reste} FCFA)")
    commande.paiements.append(
        Paiement(
            montant=donnees.montant,
            moyen=donnees.moyen,
            reference=(donnees.reference or "").strip() or None,
            encaisse_par=principal.id,
        )
    )
    commande.montant_paye += donnees.montant
    journaliser(
        session,
        JournalAudit,
        action="commande.encaissement",
        acteur_id=principal.id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"montant": donnees.montant, "moyen": donnees.moyen.value},
    )
    await session.commit()
    return vue_gestion(await acces.charger(session, reference))


def _ligne_devis(position: int, ligne: LigneDevis, produits: dict[UUID, Produit]) -> LigneCommande:
    if ligne.produit_id is None:
        if not ligne.libelle or ligne.prix_unitaire is None:
            raise HTTPException(_422, "Une ligne libre demande un libellé et un prix")
        return LigneCommande(
            libelle=ligne.libelle.strip(),
            quantite=ligne.quantite,
            prix_unitaire=ligne.prix_unitaire,
            montant=ligne.quantite * ligne.prix_unitaire,
            personnalisation=ligne.personnalisation,
            position=position,
        )
    produit = produits.get(ligne.produit_id)
    if produit is None or not produit.est_actif:
        raise HTTPException(_422, f"Ligne {position + 1} : {INDISPONIBLE}")
    if not produit.vendable_en_ligne:
        raise HTTPException(_422, f"{produit.nom} : {PHARMACIEN}")
    variante = next((v for v in produit.variantes if v.id == ligne.variante_id), None)
    if ligne.variante_id is None and any(v.est_active for v in produit.variantes):
        raise HTTPException(_422, f"{produit.nom} : {VARIANTE_REQUISE}")
    if ligne.variante_id is not None and (variante is None or not variante.est_active):
        raise HTTPException(_422, f"{produit.nom} : {VARIANTE_INDISPONIBLE}")
    prix = ligne.prix_unitaire
    if prix is None:
        prix = prix_catalogue(produit, variante, professionnel=False) or 0
    return LigneCommande(
        produit_id=produit.id,
        variante_id=variante.id if variante else None,
        libelle=(ligne.libelle or "").strip() or libelle(produit, variante),
        sku=variante.sku if variante else None,
        quantite=ligne.quantite,
        prix_unitaire=prix,
        montant=ligne.quantite * prix,
        personnalisation=ligne.personnalisation if produit.personnalisable else None,
        position=position,
    )


@routeur.put("/commandes/{reference}/devis", summary="Établir ou corriger un devis, et l'envoyer")
async def emettre_devis(
    reference: str,
    donnees: EmissionDevis,
    request: Request,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CommandeGestion:
    commande = await acces.charger(session, reference)
    if Statut(commande.statut) not in DEVIS_MODIFIABLES:
        raise HTTPException(_409, "Ce devis ne peut plus être modifié")
    produits = await charger_produits(
        session, (ligne.produit_id for ligne in donnees.lignes if ligne.produit_id)
    )
    lignes = [_ligne_devis(i, ligne, produits) for i, ligne in enumerate(donnees.lignes)]
    sous_total = sum(ligne.montant for ligne in lignes)
    frais = (
        donnees.frais_livraison
        if donnees.frais_livraison is not None
        else frais_de_livraison(ModeLivraison(commande.mode_livraison), commande.zone)
    )
    if donnees.remise > sous_total + frais:
        raise HTTPException(_422, "La remise dépasse le montant du devis")
    validite = donnees.validite_jours or _parametres(request).validite_devis_jours
    commande.lignes = lignes
    commande.sous_total = sous_total
    commande.frais_livraison = frais
    commande.remise = donnees.remise
    commande.total = sous_total + frais - donnees.remise
    commande.devis_emis_le = datetime.now(UTC)
    commande.devis_valable_jusqu_au = aujourd_hui() + timedelta(days=validite)
    await operations.appliquer_statut(
        session, commande, Statut.DEVIS_ENVOYE, principal.id, donnees.note.strip()
    )
    journaliser(
        session,
        JournalAudit,
        action="devis.emis",
        acteur_id=principal.id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"total": commande.total, "lignes": len(lignes), "validite_jours": validite},
    )
    await session.commit()
    return vue_gestion(await acces.charger(session, reference))


@routeur.get("/commandes/{reference}/devis.pdf", summary="Devis en PDF")
async def devis_en_pdf(
    reference: str,
    request: Request,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> Response:
    return reponse_devis(await acces.charger(session, reference), _parametres(request))


@routeur.get("/zones-livraison", summary="Toutes les zones, actives ou non")
async def lister_zones(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[ZoneGestion]:
    requete = select(ZoneLivraison).order_by(ZoneLivraison.position, ZoneLivraison.nom)
    return [ZoneGestion.model_validate(z) for z in (await session.execute(requete)).scalars()]


@routeur.post("/zones-livraison", status_code=status.HTTP_201_CREATED, summary="Ajouter une zone")
async def creer_zone(
    donnees: CreationZone,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> ZoneGestion:
    zone = ZoneLivraison(**donnees.model_dump())
    session.add(zone)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(_409, "Ce slug de zone est déjà utilisé") from exc
    journaliser(
        session,
        JournalAudit,
        action="zone.creee",
        acteur_id=principal.id,
        objet_type="zone_livraison",
        objet_id=zone.id,
        details={"frais": zone.frais},
    )
    await session.commit()
    return ZoneGestion.model_validate(zone)


@routeur.patch("/zones-livraison/{zone_id}", summary="Modifier une zone (frais, délai…)")
async def modifier_zone(
    zone_id: UUID,
    donnees: ModificationZone,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> ZoneGestion:
    zone = await session.get(ZoneLivraison, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    for champ, valeur in changements.items():
        setattr(zone, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="zone.modifiee",
        acteur_id=principal.id,
        objet_type="zone_livraison",
        objet_id=zone.id,
        details=changements,
    )
    await session.commit()
    await session.refresh(zone)
    return ZoneGestion.model_validate(zone)


@routeur.post("/commandes/{reference}/facture", summary="Émettre la facture sans attendre")
async def emettre_facture(
    reference: str,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> CommandeGestion:
    commande = await acces.charger(session, reference)
    if Statut(commande.statut) in SANS_ENCAISSEMENT:
        raise HTTPException(_409, "Seule une commande confirmée peut être facturée")
    facture = await factures.emettre(session, commande, principal.id)
    journaliser(
        session,
        JournalAudit,
        action="facture.emise",
        acteur_id=principal.id,
        objet_type="commande",
        objet_id=commande.reference,
        details={"facture": facture.reference, "montant": facture.montant},
    )
    await session.commit()
    return vue_gestion(await acces.charger(session, reference))


@routeur.get("/commandes/{reference}/facture.pdf", summary="Facture en PDF")
async def facture_en_pdf(
    reference: str,
    request: Request,
    _: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> Response:
    return reponse_facture(await acces.charger(session, reference), _parametres(request))


@routeur.get("/livraisons", summary="Feuille de route : à livrer et en cours de livraison")
async def livraisons(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[ArretLivraison]:
    requete = (
        acces.requete_resumes()
        .where(
            Commande.mode_livraison == ModeLivraison.LIVRAISON,
            Commande.statut.in_([Statut.PRETE, Statut.EN_LIVRAISON]),
        )
        .order_by(ZoneLivraison.position, Commande.date_promise, Commande.numero)
    )
    lignes = list(await session.execute(requete))
    livreurs = {
        livreur.id: livreur.nom
        for livreur in await session.scalars(
            select(Livreur).where(
                Livreur.id.in_({c.livreur_id for c, _, _ in lignes if c.livreur_id})
            )
        )
    }
    return [
        ArretLivraison(
            reference=c.reference,
            statut=Statut(c.statut),
            client=c.etablissement or c.nom_client,
            telephone=c.telephone,
            zone_nom=zone,
            adresse=c.adresse,
            reste_a_payer=c.reste_a_payer,
            nombre_articles=nombre,
            date_promise=c.date_promise,
            livreur_id=c.livreur_id,
            livreur_nom=livreurs.get(c.livreur_id) if c.livreur_id else None,
        )
        for c, zone, nombre in lignes
    ]


@routeur.get("/livreurs", summary="Livreurs")
async def lister_livreurs(
    _: Principal = Depends(equipe), session: AsyncSession = Depends(session_db)
) -> list[LivreurVue]:
    livreurs = await session.scalars(select(Livreur).order_by(Livreur.nom))
    return [LivreurVue.model_validate(livreur) for livreur in livreurs]


@routeur.post("/livreurs", status_code=status.HTTP_201_CREATED, summary="Ajouter un livreur")
async def creer_livreur(
    donnees: CreationLivreur,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> LivreurVue:
    telephone = operations.telephone(donnees.telephone)
    if await session.scalar(
        select(Livreur.id).where(Livreur.telephone == telephone, Livreur.est_actif)
    ):
        raise HTTPException(_409, "Un livreur actif a déjà ce numéro")
    livreur = Livreur(nom=donnees.nom.strip(), telephone=telephone)
    session.add(livreur)
    await session.flush()
    journaliser(
        session,
        JournalAudit,
        action="livreur.cree",
        acteur_id=principal.id,
        objet_type="livreur",
        objet_id=livreur.id,
    )
    await session.commit()
    return LivreurVue.model_validate(livreur)


@routeur.patch("/livreurs/{livreur_id}", summary="Modifier ou désactiver un livreur")
async def modifier_livreur(
    livreur_id: UUID,
    donnees: ModificationLivreur,
    principal: Principal = Depends(equipe),
    session: AsyncSession = Depends(session_db),
) -> LivreurVue:
    livreur = await session.get(Livreur, livreur_id)
    if livreur is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Livreur introuvable")
    changements = donnees.model_dump(exclude_unset=True)
    if "telephone" in changements:
        changements["telephone"] = operations.telephone(changements["telephone"])
    for champ, valeur in changements.items():
        setattr(livreur, champ, valeur)
    journaliser(
        session,
        JournalAudit,
        action="livreur.modifie",
        acteur_id=principal.id,
        objet_type="livreur",
        objet_id=livreur.id,
        details={"champs": sorted(changements)},
    )
    await session.commit()
    await session.refresh(livreur)
    return LivreurVue.model_validate(livreur)
