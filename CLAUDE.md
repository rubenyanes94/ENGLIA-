# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

English Academy — an online English academy with AI tutors (open-source LLM agents),
structured around the CEFR (Common European Framework of Reference for Languages, A1–C2).
This is an early-stage project (currently "Paso 1 / Step 1": just enough to prove the API,
Postgres, and Redis talk to each other). Expect most backend/frontend structure (routers,
models, agents, components) to not exist yet — you will likely be building it from scratch.

Written mostly in Spanish (code comments, README, commit style) — match that when editing
existing files; ask the user if unsure which language new user-facing text should be in.

## Stack

- **Backend:** Python + FastAPI + SQLAlchemy 2.0 (async, via `asyncpg`) + PostgreSQL with
  `pgvector` (for future agent semantic memory/embeddings) + Redis (cache / short-term
  conversational memory) + Alembic (migrations, not yet initialized) + pydantic-settings.
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + FontAwesome.
- **Infra:** Docker Compose, designed primarily for GitHub Codespaces / VS Code Dev Containers.

## Commands

There is no test suite, linter, or formatter configured yet in either backend or frontend —
don't assume `pytest`, `ruff`, `eslint`, etc. exist until you check `requirements.txt` /
`package.json` again or the user adds them.

### Running the stack

Preferred: GitHub Codespaces. Opening the repo there auto-builds `.devcontainer` and starts
`db`, `redis`, `backend`, `frontend` in the background. The backend container runs `sleep
infinity` under Codespaces (see `.devcontainer/docker-compose.yml`) so you start uvicorn
manually to see logs:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Local Docker Compose (no Codespaces) instead runs the backend's `uvicorn --reload` command
automatically:

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000/health
- Frontend: http://localhost:5173

### Backend only (outside Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend only (outside Docker)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build       # production build
npm run preview     # preview the production build
```

## Architecture

### Backend (`backend/app`)

- `main.py` — FastAPI app instance, CORS (wide open in dev — all origins/methods/headers),
  and the two existing routes: `/` and `/health`. `/health` is the integration smoke test —
  it round-trips a query through Postgres (SQLAlchemy async session) and pings Redis, and is
  what the frontend polls on load to confirm the infra is wired up correctly. New routers
  should follow this dependency-injection pattern (`Depends(get_db)`) rather than importing
  a global session.
- `core/config.py` — single `Settings` (pydantic-settings) object read from env vars /
  `.env`, exported as `settings`. Add new config values here rather than reading `os.environ`
  directly elsewhere.
- `core/db.py` — async SQLAlchemy engine + `AsyncSessionLocal` sessionmaker, and the
  `get_db()` FastAPI dependency (one session per request, closed automatically). Future
  models/routers should depend on `get_db`, not create their own engine/session.
- Redis client is instantiated directly in `main.py` at module scope
  (`redis_client = aioredis.from_url(...)`) — there's no `core/redis.py` abstraction yet.

Alembic is listed as a dependency but not yet initialized (no `alembic/` directory or
`alembic.ini`) — the DB schema for anything beyond the `pgvector` extension doesn't exist
yet. `infra/postgres/init.sql` only enables the `vector` extension on first container start.

### Frontend (`frontend/src`)

Currently just a single-page health-check UI (`App.tsx`) — no routing, state management, or
component library set up yet.

The one piece of non-obvious logic worth knowing before touching it is `resolveApiUrl()` in
`App.tsx`: it deliberately avoids hardcoding `http://localhost:8000`. In GitHub Codespaces,
each forwarded port lives on its own subdomain (e.g. `*-5173.app.github.dev` vs
`*-8000.app.github.dev`), so `localhost` from the browser's perspective doesn't reach the
Codespace at all. The function derives the backend URL from the current browser URL by
swapping the port (or the `-5173.`/`-8000.` subdomain fragment), and only falls back to
`VITE_API_URL` if that env var is explicitly set. Keep this in mind for any new frontend code
that needs to call the backend — reuse `resolveApiUrl`/`API_URL` rather than hardcoding a host.

### Docker Compose topology

Root `docker-compose.yml` defines the "real" 4-service stack (`db`, `redis`, `backend`,
`frontend`) usable standalone on any server. `.devcontainer/docker-compose.yml` is an overlay
that Codespaces merges on top of it — it only patches the `backend` service (mounts the
whole repo, replaces its command with `sleep infinity`) so a single VS Code window can browse
and edit both `backend/` and `frontend/`, and so uvicorn is started manually instead of
auto-launching. Don't confuse the two files: editing service definitions for production/local
Docker use belongs in the root file; editor-only conveniences belong in the devcontainer
overlay.

Services talk to each other by Docker Compose service name, not `localhost` (e.g.
`DATABASE_URL` in `.env` points at host `db`, not `localhost`).
