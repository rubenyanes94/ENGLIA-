# Frontend en PRODUCCIÓN: se compila con Node y se sirve con Caddy.
# El de desarrollo es Dockerfile.dev (lo nombra el docker-compose).
#
# Dos etapas a propósito. La imagen final NO lleva Node, ni npm, ni
# node_modules, ni el código fuente: solo los archivos compilados y un
# servidor de 50 MB. Menos cosas que actualizar y menos superficie que
# puedan atacar.
#
# El servidor de desarrollo de Vite (el del Dockerfile normal) no debe
# ver producción nunca: no compila, no comprime, no cachea y expone el
# código fuente.

FROM node:20-slim AS build
WORKDIR /app

# Primero las dependencias, para que un cambio en el código no vuelva a
# descargarlas enteras. `npm ci` y no `npm install`: instala EXACTAMENTE
# lo que dice package-lock.json, así lo que se compila aquí es lo mismo
# que se probó en desarrollo.
COPY package*.json ./
RUN npm ci

COPY . .
# VITE_API_URL se queda sin definir a propósito: el frontend pide "/api"
# en su mismo origen y quien reenvía es el Caddy de abajo (ver Caddyfile).
RUN npm run build


FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
# Railway inyecta $PORT; el 8080 es solo para correr la imagen a mano.
EXPOSE 8080
