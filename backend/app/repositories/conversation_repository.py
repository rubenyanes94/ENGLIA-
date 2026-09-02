import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.models import AgentPersona, ConversationMessage, ConversationSession


async def create_session(
    db: AsyncSession, user_id: uuid.UUID, persona: AgentPersona, module_id: uuid.UUID | None = None
) -> ConversationSession:
    session = ConversationSession(user_id=user_id, persona_id=persona.id, module_id=module_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> ConversationSession | None:
    """Trae la sesión con `persona` (+ su nivel) y `module` YA cargados
    (joinedload). Con SQLAlchemy async, acceder a una relación sin
    haberla precargado explícitamente revienta (MissingGreenlet) — aquí
    las pedimos de una vez. `module` puede venir None sin problema (la
    sesión no tiene por qué estar atada a un módulo)."""
    result = await db.execute(
        select(ConversationSession)
        .options(
            joinedload(ConversationSession.persona).joinedload(AgentPersona.level),
            joinedload(ConversationSession.module),
        )
        .where(ConversationSession.id == session_id)
    )
    return result.scalars().first()


async def end_session(db: AsyncSession, session: ConversationSession) -> ConversationSession:
    session.ended_at = func.now()
    await db.commit()
    await db.refresh(session)
    return session


async def add_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    corrections: list[dict] | None = None,
) -> ConversationMessage:
    message = ConversationMessage(session_id=session_id, role=role, content=content, corrections=corrections)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(db: AsyncSession, session_id: uuid.UUID) -> list[ConversationMessage]:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at)
    )
    return list(result.scalars().all())


async def set_summary(db: AsyncSession, session: ConversationSession, summary: str, embedding: list[float]) -> None:
    """Lo llama el worker de Celery al terminar de resumir una sesión."""
    session.summary = summary
    session.summary_embedding = embedding
    await db.commit()


async def find_similar_past_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_embedding: list[float],
    exclude_session_id: uuid.UUID,
    limit: int = 2,
) -> list[str]:
    """Busca, entre las sesiones YA resumidas de este alumno, las más
    parecidas semánticamente al mensaje actual — esto es la memoria de
    LARGO plazo en acción: no "los últimos N resúmenes", sino "los
    resúmenes más RELEVANTES para lo que se está hablando ahora".

    `cosine_distance` es el operador de pgvector: 0 = idénticos,
    2 = opuestos. Ordenar ascendente = del más parecido al más distinto.
    """
    result = await db.execute(
        select(ConversationSession.summary)
        .where(
            ConversationSession.user_id == user_id,
            ConversationSession.id != exclude_session_id,
            ConversationSession.summary_embedding.is_not(None),
        )
        .order_by(ConversationSession.summary_embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return [row[0] for row in result.all()]
