from redis import asyncio as aioredis

from app.core.config import settings

# Cliente único, reutilizado por toda la app (health check, memoria de
# conversación...). Un solo pool de conexiones, no uno por módulo.
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
