# Image d'un service Python (comptes, boutique…). Construite depuis la racine du dépôt :
#   docker build -f infra/python.Dockerfile --build-arg SERVICE=comptes .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

ARG SERVICE
ENV SERVICE=${SERVICE} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY socle socle
COPY services services
RUN uv sync --frozen --no-dev --package "${SERVICE}" \
    && useradd --system --no-create-home service \
    && mkdir -p /medias && chown service /medias

WORKDIR /app/services/${SERVICE}
USER service
EXPOSE 8000

# Les migrations s'appliquent au démarrage, puis le service écoute.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn ${SERVICE}.main:creer_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
