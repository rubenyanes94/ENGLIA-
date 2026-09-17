"""Juego de completar oraciones: elige la palabra correcta y sube de nivel.

El banco de oraciones vive en app/content/sentence_game.json, escrito y
revisado a mano: cada oración tiene una sola opción correcta. No se genera
con el modelo porque, al hacerlo con los exámenes, salieron preguntas con
dos respuestas válidas, y aquí eso le quitaría un acierto a quien respondió
bien.

La dificultad sube con el alumno: empieza en el nivel 1 (verbo to be) y
cada LEVEL_UP_GOAL aciertos pasa al siguiente, hasta el 6 (condicionales,
voz pasiva). Un fallo resta un acierto del nivel sin bajar de cero, así que
subir pide acertar con constancia y no solo insistir.
"""

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SentenceGameProgress

CONTENT = Path(__file__).resolve().parent.parent / "content" / "sentence_game.json"
LEVEL_UP_GOAL = 5
# Cuántas oraciones recientes se evitan. Por debajo de las 14 de cada
# nivel, para que siempre quede alguna por mostrar.
RECENT_WINDOW = 10


class ItemNotPendingError(Exception):
    """Se intentó responder una oración distinta de la que se mostró."""


@dataclass(frozen=True)
class Level:
    number: int
    name: str
    topic: str
    items: tuple[dict, ...]


@lru_cache(maxsize=1)
def load_levels() -> tuple[Level, ...]:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    levels = tuple(
        Level(number=raw["level"], name=raw["name"], topic=raw["topic"], items=tuple(raw["items"]))
        for raw in sorted(data["levels"], key=lambda raw: raw["level"])
    )
    # Se comprueba al cargar y no al servir: un banco roto tiene que fallar
    # al arrancar, no la primera vez que un alumno llega a esa oración.
    for level in levels:
        assert len(level.items) > RECENT_WINDOW, f"el nivel {level.number} tiene muy pocas oraciones"
        for item in level.items:
            assert item["answer"] in item["options"], f"{item['id']}: la respuesta no está entre las opciones"
    return levels


def max_level() -> int:
    return len(load_levels())


def get_level(number: int) -> Level:
    return load_levels()[number - 1]


def find_item(item_id: str) -> tuple[Level, dict] | None:
    for level in load_levels():
        for item in level.items:
            if item["id"] == item_id:
                return level, item
    return None


async def get_or_create_progress(db: AsyncSession, user_id) -> SentenceGameProgress:
    progress = await db.get(SentenceGameProgress, user_id)
    if progress is None:
        progress = SentenceGameProgress(
            user_id=user_id,
            level=1,
            level_progress=0,
            total_answered=0,
            total_correct=0,
            streak=0,
            best_streak=0,
            recent_item_ids=[],
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
    return progress


async def next_item(db: AsyncSession, progress: SentenceGameProgress) -> dict:
    """La oración que toca responder.

    Si ya había una pendiente, devuelve esa misma y no una nueva: recargar
    la página no puede servir para saltarse una oración difícil.
    """
    if progress.pending_item_id:
        found = find_item(progress.pending_item_id)
        if found is not None:
            return found[1]

    level = get_level(progress.level)
    fresh = [item for item in level.items if item["id"] not in progress.recent_item_ids]
    item = random.choice(fresh or list(level.items))

    progress.pending_item_id = item["id"]
    await db.commit()
    return item


@dataclass
class AnswerResult:
    correct: bool
    correct_answer: str
    explanation_es: str
    leveled_up: bool


async def answer(db: AsyncSession, progress: SentenceGameProgress, item_id: str, given: str) -> AnswerResult:
    if progress.pending_item_id != item_id:
        raise ItemNotPendingError()

    found = find_item(item_id)
    if found is None:
        raise ItemNotPendingError()
    _, item = found

    correct = given.strip().lower() == item["answer"].strip().lower()
    leveled_up = False

    progress.total_answered += 1
    if correct:
        progress.total_correct += 1
        progress.streak += 1
        progress.best_streak = max(progress.best_streak, progress.streak)
        progress.level_progress += 1
        if progress.level_progress >= LEVEL_UP_GOAL and progress.level < max_level():
            progress.level += 1
            progress.level_progress = 0
            leveled_up = True
        # En el último nivel no hay a dónde subir: el contador se queda en
        # la meta en vez de crecer sin fin.
        progress.level_progress = min(progress.level_progress, LEVEL_UP_GOAL)
    else:
        progress.streak = 0
        progress.level_progress = max(progress.level_progress - 1, 0)

    # Lista nueva y no .append(): SQLAlchemy no detecta cambios dentro de
    # un ARRAY, solo que se asigna uno distinto.
    progress.recent_item_ids = [*progress.recent_item_ids, item_id][-RECENT_WINDOW:]
    progress.pending_item_id = None
    await db.commit()

    return AnswerResult(
        correct=correct,
        correct_answer=item["answer"],
        explanation_es=item["explanation_es"],
        leveled_up=leveled_up,
    )
