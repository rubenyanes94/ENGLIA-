from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.redis import redis_client
from app.routers import admin, auth, billing, chat, events, levels, modules, users, webhooks

app = FastAPI(title="English Academy API", version="0.1.0")

# Archivos generados (hoy: audio de lecciones narradas por James — ver
# app/media/storage.py). StaticFiles exige que el directorio ya exista
# al montar, por eso el mkdir aquí antes del mount.
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_root), name="media")

# En desarrollo permitimos cualquier origen para que React (puerto 5173)
# pueda llamar a la API (puerto 8000) sin bloqueos de CORS.
# En producción esto se restringe al dominio real del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(levels.router)
app.include_router(modules.router)
app.include_router(chat.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(events.router)
app.include_router(billing.router)
app.include_router(webhooks.router)


@app.get("/")
async def root() -> dict:
    return {"message": "English Academy API is running 🚀"}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """Endpoint de diagnóstico: confirma que la API puede hablar tanto
    con PostgreSQL como con Redis. Es lo primero que probaremos desde
    el frontend para validar que toda la infraestructura está viva."""
    await db.execute(text("SELECT 1"))
    pong = await redis_client.ping()

    return {
        "status": "ok",
        "postgres": "connected",
        "redis": "connected" if pong else "unreachable",
    }
