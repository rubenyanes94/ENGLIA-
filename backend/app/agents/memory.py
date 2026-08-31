"""Memoria de CORTO plazo: el historial de turnos de una sesión activa,
guardado en Redis con TTL. Es lo que le pasamos al LLM en cada llamada
para que la conversación tenga continuidad.

No confundir con la memoria PERMANENTE (tabla `conversation_messages` en
Postgres, ver app/repositories/conversation_repository.py): esta de aquí
puede expirar y no pasa nada, porque el historial de verdad ya quedó
guardado en la base de datos en el mismo turno.
"""

import json
import uuid

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from redis.asyncio import Redis

from app.core.config import settings


def _redis_key(session_id: uuid.UUID) -> str:
    return f"chat:session:{session_id}:messages"


class RedisConversationMemory:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_history(self, session_id: uuid.UUID) -> list[BaseMessage]:
        """Recupera el historial ya convertido a mensajes de LangChain,
        listos para pasarle directamente al grafo del agente."""
        raw = await self._redis.get(_redis_key(session_id))
        if not raw:
            return []

        turns = json.loads(raw)
        return [
            HumanMessage(content=turn["content"]) if turn["role"] == "user" else AIMessage(content=turn["content"])
            for turn in turns
        ]

    async def append_turn(self, session_id: uuid.UUID, user_content: str, assistant_content: str) -> None:
        """Añade el par (pregunta del alumno, respuesta del tutor) al
        historial y renueva el TTL: mientras la conversación siga activa,
        no se olvida a mitad de charla."""
        raw = await self._redis.get(_redis_key(session_id))
        turns = json.loads(raw) if raw else []

        turns.append({"role": "user", "content": user_content})
        turns.append({"role": "assistant", "content": assistant_content})

        await self._redis.set(
            _redis_key(session_id),
            json.dumps(turns),
            ex=settings.chat_session_ttl_minutes * 60,
        )

    async def clear(self, session_id: uuid.UUID) -> None:
        """Se llama al cerrar una sesión: libera la memoria de corto plazo
        ya mismo, sin esperar a que expire el TTL sola."""
        await self._redis.delete(_redis_key(session_id))
