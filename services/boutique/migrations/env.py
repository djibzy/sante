import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from boutique.config import ParametresBoutique
from boutique.models import Base

config = context.config
target_metadata = Base.metadata

# Index créés à la main dans une migration (expressions que les modèles ne décrivent pas) :
# l'autogénération ne doit pas proposer de les supprimer.
INDEX_HORS_MODELES = {"ix_produits_nom_trgm"}


def _inclure(objet: object, nom: str | None, type_: str, reflete: bool, compare: object) -> bool:
    return not (type_ == "index" and reflete and nom in INDEX_HORS_MODELES)


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or ParametresBoutique().database_url


def _executer(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=_inclure,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _executer_en_ligne() -> None:
    moteur = create_async_engine(_url(), poolclass=NullPool)
    async with moteur.connect() as connection:
        await connection.run_sync(_executer)
    await moteur.dispose()


if context.is_offline_mode():
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_executer_en_ligne())
