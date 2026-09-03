#!/usr/bin/env bash
# Arranca uvicorn automáticamente cada vez que el Codespace (re)inicia,
# para no tener que acordarte de hacerlo a mano en la terminal (ver
# CLAUDE.md → "Running the stack"). Se ejecuta como postStartCommand
# desde devcontainer.json, dentro del contenedor "backend".
set -uo pipefail

# "/app" y no "/workspaces/ENGLIA-/backend" a propósito: /app es el mount
# que YA declara el docker-compose.yml de la raíz para "backend"
# (./backend:/app), así que funciona igual sin depender del montaje extra
# del editor en .devcontainer/docker-compose.yml.
BACKEND_DIR="/app"
LOG_FILE="/tmp/uvicorn.log"
PID_FILE="/tmp/uvicorn.pid"

# Si ya hay un uvicorn vivo (p. ej. reconexión a un Codespace que no se
# reinició de verdad), no lances uno nuevo: pelearía por el puerto 8000
# con el que ya está corriendo.
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "[start-backend] uvicorn ya está corriendo (PID $(cat "$PID_FILE")), no se relanza."
  exit 0
fi

cd "$BACKEND_DIR" || { echo "[start-backend] no existe $BACKEND_DIR"; exit 1; }

# LLM_MODEL a mano, explícito: la variable de entorno HORNEADA en este
# contenedor (fijada al crearlo) puede haber quedado desactualizada
# frente a lo que dice docker-compose.yml hoy — pasó de verdad: el
# contenedor seguía con "llama3.2:1b" (1.3GB, tumbaba Ollama por falta de
# RAM) mucho después de que el compose ya pidiera "qwen2.5:0.5b" (400MB),
# porque nada volvió a CREAR el contenedor desde entonces. Sin este
# override, un reinicio automático reintroduciría ese crash en silencio.
export LLM_MODEL="${LLM_MODEL:-qwen2.5:0.5b}"

# db/redis ya están "healthy" en este punto: docker-compose.yml declara
# depends_on con condition: service_healthy, y ese chequeo lo hace Docker
# Compose ANTES de crear/arrancar el contenedor "backend" — no hace falta
# esperar aquí de nuevo.
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "[start-backend] uvicorn arrancado en segundo plano (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"
