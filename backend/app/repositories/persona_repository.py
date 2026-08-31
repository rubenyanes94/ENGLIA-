from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import AgentPersona, CEFRLevel


async def get_active_persona_by_level_code(db: AsyncSession, level_code: str) -> AgentPersona | None:
    result = await db.execute(
        select(AgentPersona)
        .join(CEFRLevel)
        .where(CEFRLevel.code == level_code.upper(), AgentPersona.is_active.is_(True))
        .options(joinedload(AgentPersona.level))
        .limit(1)
    )
    return result.scalars().first()
