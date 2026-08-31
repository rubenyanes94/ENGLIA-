from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.redis import redis_client
from app.routers import auth, chat, levels, modules, users

app = FastAPI(title="English Academy API", version="0.1.0")

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
