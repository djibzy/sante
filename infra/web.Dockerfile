# Image de l'interface de la boutique, construite depuis le dossier web/ :
#   docker build -f infra/web.Dockerfile web
FROM node:22-slim AS construction
WORKDIR /web
COPY charte charte
COPY boutique boutique
RUN cd boutique && npm ci && npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=construction /web/boutique/.output .output
ENV HOST=0.0.0.0 PORT=3000 NODE_ENV=production
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
