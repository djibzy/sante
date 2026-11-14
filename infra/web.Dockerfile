# Image d'une interface Nuxt, construite depuis le dossier web/ avec la charte commune :
#   docker build -f infra/web.Dockerfile --build-arg APP=boutique web
#   docker build -f infra/web.Dockerfile --build-arg APP=prestations web
FROM node:22-slim AS construction
ARG APP=boutique
WORKDIR /web
COPY charte charte
COPY ${APP} ${APP}
RUN cd ${APP} && npm ci && npm run build

FROM node:22-slim
ARG APP=boutique
WORKDIR /app
COPY --from=construction /web/${APP}/.output .output
ENV HOST=0.0.0.0 PORT=3000 NODE_ENV=production
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
