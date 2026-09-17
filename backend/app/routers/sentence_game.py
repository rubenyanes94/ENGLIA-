import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import SentenceGameProgress, User
from app.schemas.sentence_game import GameAnswerIn, GameAnswerOut, GameItemOut, GameNextOut, GameStateOut
from app.services import sentence_game as game

router = APIRouter(prefix="/game/sentences", tags=["game"])


def _state(progress: SentenceGameProgress) -> GameStateOut:
    level = game.get_level(progress.level)
    return GameStateOut(
        level=progress.level,
        max_level=game.max_level(),
        level_name=level.name,
        level_topic=level.topic,
        level_progress=progress.level_progress,
        level_goal=game.LEVEL_UP_GOAL,
        total_answered=progress.total_answered,
        total_correct=progress.total_correct,
        streak=progress.streak,
        best_streak=progress.best_streak,
    )


@router.post("/next", response_model=GameNextOut)
async def next_sentence(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameNextOut:
    """La oración que toca. POST y no GET porque la deja marcada como
    pendiente: es la única que el alumno puede responder a continuación."""
    progress = await game.get_or_create_progress(db, current_user.id)
    item = await game.next_item(db, progress)
    # Opciones barajadas en cada entrega: con la correcta siempre en la
    # misma posición, se aprendería el sitio y no la palabra.
    options = list(item["options"])
    random.shuffle(options)
    return GameNextOut(
        item=GameItemOut(id=item["id"], sentence=item["sentence"], options=options),
        state=_state(progress),
    )


@router.post("/answer", response_model=GameAnswerOut)
async def answer_sentence(
    payload: GameAnswerIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameAnswerOut:
    progress = await game.get_or_create_progress(db, current_user.id)
    try:
        result = await game.answer(db, progress, payload.item_id, payload.answer)
    except game.ItemNotPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa oración ya no está pendiente. Pide la siguiente.",
        )
    return GameAnswerOut(
        correct=result.correct,
        correct_answer=result.correct_answer,
        explanation_es=result.explanation_es,
        leveled_up=result.leveled_up,
        state=_state(progress),
    )
