import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embeddings import embed_text
from app.agents.graph import run_tutor_turn
from app.agents.memory import RedisConversationMemory
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.redis import redis_client
from app.models import ConversationSession, User
from app.repositories import conversation_repository, event_repository, persona_repository
from app.workers.tasks import summarize_session
from app.schemas.chat import (
    CreateSessionRequest,
    CreateSessionResponse,
    EndSessionResponse,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])

memory = RedisConversationMemory(redis_client)


async def _get_owned_session(db: AsyncSession, session_id: uuid.UUID, current_user: User) -> ConversationSession:
    """Trae la sesión y confirma que es del usuario autenticado.

    Ojo con la diferencia entre 404 y 403 aquí a propósito: si la sesión
    es de OTRO alumno, devolvemos 404 (no 403) para no confirmarle a un
    atacante que ese session_id existe — es el mismo criterio que
    seguiríamos con cualquier recurso ajeno.
    """
    session = await conversation_repository.get_session(db, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return session


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateSessionResponse:
    """Abre una conversación nueva con el tutor del nivel indicado."""
    persona = await persona_repository.get_active_persona_by_level_code(db, payload.level_code)
    if persona is None:
        raise HTTPException(
            status_code=404,
            detail=f"No hay un tutor activo configurado para el nivel '{payload.level_code}'.",
        )

    session = await conversation_repository.create_session(db, current_user.id, persona)

    return CreateSessionResponse(
        session_id=session.id,
        persona_name=persona.name,
        level_code=payload.level_code.upper(),
    )


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: uuid.UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SendMessageResponse:
    """Envía un mensaje del alumno y devuelve la respuesta del tutor,
    manteniendo el contexto de toda la sesión (memoria de corto plazo)."""
    session = await _get_owned_session(db, session_id, current_user)
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="Esta sesión ya terminó. Abre una nueva.")

    # 1. Recuperamos el historial de la sesión (memoria de corto plazo, Redis).
    history = await memory.get_history(session_id)

    # 1b. Solo en el PRIMER turno de la sesión, buscamos memoria semántica
    #     de largo plazo: resúmenes de sesiones pasadas de este alumno
    #     parecidos a lo que está diciendo ahora. No lo hacemos en cada
    #     turno para no pagar una llamada de embeddings de más cada vez.
    long_term_context = None
    if not history:
        query_embedding = await embed_text(payload.message)
        similar_summaries = await conversation_repository.find_similar_past_sessions(
            db, current_user.id, query_embedding, exclude_session_id=session_id
        )
        if similar_summaries:
            long_term_context = "\n".join(f"- {s}" for s in similar_summaries)

    # 2. El agente conversa Y detecta errores en paralelo (ver app/agents/graph.py).
    turn = await run_tutor_turn(
        session.persona,
        history,
        payload.message,
        level_code=session.persona.level.code,
        long_term_context=long_term_context,
    )

    # 3. Actualizamos Redis (para el próximo turno de esta misma sesión)...
    await memory.append_turn(session_id, payload.message, turn["reply"])

    # 4. ...y dejamos constancia permanente en Postgres (memoria de largo
    #    plazo), pase lo que pase con Redis más adelante. Las correcciones
    #    van en el mensaje del ALUMNO: es donde ocurrió el error.
    await conversation_repository.add_message(
        db, session_id, role="user", content=payload.message, corrections=turn["corrections"] or None
    )
    await conversation_repository.add_message(db, session_id, role="assistant", content=turn["reply"])

    return SendMessageResponse(
        session_id=session_id,
        reply=turn["reply"],
        persona_name=session.persona.name,
        corrections=turn["corrections"],
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """Historial completo y permanente de la sesión (desde Postgres, no
    desde Redis) — útil para repintar el chat si el alumno recarga la página."""
    await _get_owned_session(db, session_id, current_user)
    return await conversation_repository.list_messages(db, session_id)


@router.post("/sessions/{session_id}/end", response_model=EndSessionResponse)
async def end_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EndSessionResponse:
    """Cierra la sesión: libera la memoria de corto plazo (Redis) ya, y
    encola el resumen + embedding (memoria de largo plazo) en un worker
    de Celery — no bloqueamos la respuesta HTTP esperando a que un LLM
    genere el resumen."""
    session = await _get_owned_session(db, session_id, current_user)

    await conversation_repository.end_session(db, session)
    await memory.clear(session_id)
    summarize_session.delay(str(session_id))
    await event_repository.record(
        db,
        current_user.id,
        "chat_session_ended",
        {"session_id": str(session_id), "level_code": session.persona.level.code},
    )

    return EndSessionResponse(session_id=session_id)
