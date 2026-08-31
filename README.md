# English Academy 🇬🇧

Academia de inglés online con tutores de IA (agentes LLM open source), estructurada
según el Marco Común Europeo de Referencia para las Lenguas (MCER, niveles A1–C2).

## Stack

- **Backend:** Python + FastAPI + SQLAlchemy (async) + PostgreSQL (`pgvector`) + Redis
- **Agentes IA:** LangGraph + LangChain, sobre un LLM open source servido vía Ollama
  (dev) / vLLM o NVIDIA NIM (producción) — endpoint OpenAI-compatible en ambos casos
- **Frontend:** React + TypeScript + Tailwind CSS + FontAwesome
- **Infraestructura:** Docker Compose, pensado para GitHub Codespaces

## Cómo levantar el proyecto

### Opción A — GitHub Codespaces (recomendado)

1. Abre este repositorio en Codespaces ("Code" → "Create codespace on main").
2. Espera a que termine de construir el `.devcontainer` (primera vez tarda unos minutos).
3. Cuando VS Code termine de cargar, ya tienes 5 servicios corriendo en segundo plano:
   `db`, `redis`, `ollama`, `backend` y `frontend`.
4. Abre una terminal dentro de VS Code y arranca la API manualmente (así ves los logs):

   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Descarga el modelo LLM (solo la primera vez; ~1.3GB, tarda unos minutos):

   ```bash
   docker compose exec ollama ollama pull llama3.2:1b
   ```

6. Aplica las migraciones y siembra los datos base:

   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python -m app.scripts.seed_cefr_levels
   docker compose exec backend python -m app.scripts.seed_agent_personas
   ```

7. En la pestaña "Ports" verás los puertos reenviados: `8000` (API) y `5173` (frontend).
   Ábrelos para comprobar que todo está conectado.

### Opción B — Docker Compose en local (sin Codespaces)

```bash
cp .env.example .env
docker compose up --build
# primera vez:
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_cefr_levels
docker compose exec backend python -m app.scripts.seed_agent_personas
```

- API: http://localhost:8000/health
- Frontend: http://localhost:5173
- Probar el flujo completo (registro → login → chat):
  ```bash
  # 1. Registro (devuelve el token directamente, auto-login)
  TOKEN=$(curl -s -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email": "tu@email.com", "password": "contraseña123", "full_name": "Tu Nombre"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  # 2. Abrir sesión de chat con un tutor
  SESSION_ID=$(curl -s -X POST http://localhost:8000/chat/sessions \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"level_code": "A1"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

  # 3. Enviar un mensaje
  curl -X POST "http://localhost:8000/chat/sessions/$SESSION_ID/messages" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"message": "Hello!"}'
  ```

> **Nota sobre el modelo:** `llama3.2:1b` es deliberadamente pequeño para caber en
> un Codespace de 8GB de RAM junto con VS Code. Es suficiente para probar el
> pipeline (LangGraph → Ollama → respuesta), pero un modelo tan pequeño no siempre
> sigue bien instrucciones complejas del prompt (ej. "responde siempre en inglés").
> Con más RAM (16GB+) o en producción con GPU, usa `llama3.2:3b`/`8b` o el modelo
> NVIDIA Nemotron para mejor calidad — solo cambia `LLM_MODEL` en `.env`.

## Estructura

```
backend/
  app/
    core/       → config, conexión a BD (engine, Base declarativa)
    models/     → modelos SQLAlchemy (User, CEFRLevel, Module, AgentPersona...)
    schemas/    → contratos Pydantic de la API
    repositories/ → única capa que habla SQL/ORM
    routers/    → endpoints FastAPI
    agents/     → grafo LangGraph del tutor IA + cliente LLM
    scripts/    → seeds (niveles MCER, tutores IA)
  alembic/      → migraciones de base de datos
frontend/       → App React + TypeScript + Tailwind
infra/          → Configuración de infraestructura (Postgres, etc.)
.devcontainer/  → Configuración de Codespaces / VS Code Dev Containers
```

## Endpoints disponibles

Swagger interactivo (con "Try it out" y botón "Authorize" para pegar el
token): `/docs` — en Codespaces, `https://<tu-codespace>-8000.app.github.dev/docs`.

| Método | Ruta | Auth | Qué hace |
|---|---|---|---|
| GET | `/health` | — | Comprueba conexión a Postgres y Redis |
| POST | `/auth/register` | — | Crea una cuenta y devuelve un token (auto-login) |
| POST | `/auth/login` | — | Form `username`/`password` (username = email). Devuelve token |
| GET | `/auth/me` | 🔒 | Datos del usuario autenticado |
| GET | `/levels` | — | Lista los 6 niveles MCER (A1–C2) |
| POST | `/chat/sessions` | 🔒 | Abre una conversación nueva con el tutor de un nivel (`level_code`) |
| POST | `/chat/sessions/{id}/messages` | 🔒 | Envía un mensaje y recibe la respuesta del tutor, con memoria de la sesión |
| GET | `/chat/sessions/{id}/messages` | 🔒 | Historial completo y permanente de la sesión (Postgres) |
| POST | `/chat/sessions/{id}/end` | 🔒 | Cierra la sesión: libera la memoria de corto plazo (Redis); Postgres queda intacto |

🔒 = requiere header `Authorization: Bearer <token>`. Las sesiones de chat
están aisladas por usuario: intentar leer/escribir la sesión de otro
alumno devuelve `404` (no `403`, a propósito — no revelamos que el
recurso existe).
