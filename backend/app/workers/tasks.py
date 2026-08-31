"""Tareas asíncronas de Celery.

Celery, por diseño, corre código SÍNCRONO (cada worker procesa una tarea
a la vez hasta terminarla). Pero todo nuestro stack de datos y de agentes
es ASYNC (SQLAlchemy async, LangChain async). En vez de duplicar toda una
capa de repositorios en versión síncrona solo para el worker, cada tarea
abre su propio loop con `asyncio.run(...)` y reutiliza exactamente los
mismos repositorios/clientes que usa la API. Es un patrón estándar y
pragmático para este tamaño de proyecto.
"""

import asyncio
import logging
import uuid

from app.agents.embeddings import embed_text
from app.agents.summarization import summarize_transcript
from app.core.db import AsyncSessionLocal, engine
from app.repositories import conversation_repository
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="summarize_session", bind=True, max_retries=2, default_retry_delay=30)
def summarize_session(self, session_id: str) -> None:
    try:
        asyncio.run(_summarize_session_async(session_id))
    except Exception as exc:
        logger.warning("Fallo resumiendo sesión %s, reintentando...", session_id, exc_info=True)
        raise self.retry(exc=exc)


async def _summarize_session_async(session_id: str) -> None:
    try:
        async with AsyncSessionLocal() as db:
            session_uuid = uuid.UUID(session_id)

            session = await conversation_repository.get_session(db, session_uuid)
            if session is None:
                logger.warning("summarize_session: sesión %s no existe, se omite.", session_id)
                return

            messages = await conversation_repository.list_messages(db, session_uuid)
            if not messages:
                logger.info("summarize_session: sesión %s sin mensajes, nada que resumir.", session_id)
                return

            transcript = "\n".join(f"{m.role}: {m.content}" for m in messages)

            summary = await summarize_transcript(transcript, model_id=session.persona.model_id)
            embedding = await embed_text(summary)

            await conversation_repository.set_summary(db, session, summary, embedding)
            logger.info("summarize_session: sesión %s resumida y embebida.", session_id)
    finally:
        # CRÍTICO: cada tarea de Celery corre en su propio asyncio.run(),
        # es decir, su propio event loop. El engine de SQLAlchemy es un
        # objeto global (importado de app.core.db) cuyo pool de conexiones
        # queda atado al loop en el que se usó por primera vez. Si no lo
        # cerramos aquí, la SIGUIENTE tarea intentará reutilizar una
        # conexión asyncpg "viva" de un loop que ya no existe, y revienta
        # con "attached to a different loop". Al hacer dispose(), la
        # próxima tarea abre conexiones nuevas, limpias, en SU loop.
        await engine.dispose()
