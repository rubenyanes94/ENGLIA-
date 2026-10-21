#!/bin/sh
# Arranque en producción (Railway). En desarrollo NO se usa: el
# docker-compose de la raíz define su propio `command` con --reload.
#
# Un solo script para los dos procesos que corren la misma imagen, y el
# papel lo decide la variable ROLE:
#
#   ROLE=web     (por defecto) la API
#   ROLE=worker  el worker de Celery (resúmenes de sesión del tutor)
#
# Las MIGRACIONES las corre solo el web, y a propósito antes de arrancar
# uvicorn: si corrieran en los dos, dos despliegues simultáneos se
# pisarían a mitad de un ALTER TABLE. Y van aquí dentro y no en el
# "pre-deploy command" de Railway porque así el contenedor que migra es
# EXACTAMENTE el mismo que después sirve — misma imagen, mismas
# variables, misma base. Si la migración falla, el proceso no arranca y
# el despliegue se marca como roto, que es lo que debe pasar.
set -e

ROLE="${ROLE:-web}"

if [ "$ROLE" = "worker" ]; then
  echo "→ Celery worker"
  exec celery -A app.workers.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
fi

echo "→ Migraciones"
alembic upgrade head

# --host :: y no 0.0.0.0: la red privada de Railway (la que usa el
# frontend para hablar con la API sin salir a internet) es IPv6. Un
# proceso escuchando solo en IPv4 es invisible ahí dentro.
#
# $PORT lo inyecta Railway y cambia entre despliegues; uvicorn no lo lee
# solo, hay que pasárselo. El 8000 es solo para correr la imagen a mano.
echo "→ API en el puerto ${PORT:-8000}"
exec uvicorn app.main:app --host :: --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
