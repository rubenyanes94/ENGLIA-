"""Siembra un módulo de ejemplo (con lecciones y ejercicios) en A1, solo
para poder probar los endpoints de currículo/progreso end-to-end sin
depender todavía de un panel de autoría de contenido.

Uso:
    python -m app.scripts.seed_curriculum

Idempotente: si el módulo "Presentarse" en A1 ya existe, no hace nada.
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel, Exercise, Lesson, Module


async def seed_curriculum() -> None:
    async with AsyncSessionLocal() as session:
        level_result = await session.execute(select(CEFRLevel).where(CEFRLevel.code == "A1"))
        level = level_result.scalars().first()
        if level is None:
            print("No existe el nivel A1 todavía — corre antes `python -m app.scripts.seed_cefr_levels`.")
            return

        existing = await session.execute(
            select(Module).where(Module.level_id == level.id, Module.title == "Presentarse")
        )
        if existing.scalars().first() is not None:
            print("El módulo de ejemplo 'Presentarse' (A1) ya existía. Nada que insertar.")
            return

        module = Module(level_id=level.id, title="Presentarse", skill_focus="speaking", order=1)
        session.add(module)
        await session.flush()  # necesitamos module.id antes de crear sus lecciones

        lesson_1 = Lesson(
            module_id=module.id,
            title="Saludos y despedidas",
            order=1,
            content={
                "type": "text",
                "body": (
                    "En inglés, 'Hello' y 'Hi' se usan para saludar en cualquier "
                    "momento del día. 'Goodbye' y 'Bye' para despedirse."
                ),
            },
        )
        lesson_2 = Lesson(
            module_id=module.id,
            title="Decir tu nombre",
            order=2,
            content={
                "type": "text",
                "body": "'My name is...' o 'I am...' son las dos formas más comunes de decir tu nombre.",
            },
        )
        session.add_all([lesson_1, lesson_2])
        await session.flush()  # ídem: necesitamos los ids de las lecciones para los ejercicios

        exercises = [
            # stage="exam" en los dos a propósito: son los que definen si
            # el módulo de ejemplo se completa (ver
            # enrollment_repository.recompute_mastery, que solo promedia
            # ejercicios "exam"). Un módulo real tendría también
            # ejercicios "practice" (el default) antes de estos.
            Exercise(
                lesson_id=lesson_1.id,
                exercise_type="multiple_choice",
                stage="exam",
                prompt="¿Cuál de estas frases usarías para saludar por la mañana?",
                answer_key={"correct": "Good morning!", "options": ["Good morning!", "Goodbye!", "See you!"]},
            ),
            Exercise(
                lesson_id=lesson_2.id,
                exercise_type="fill_blank",
                stage="exam",
                prompt="Completa: 'My ___ is Ana.'",
                answer_key={"correct": "name"},
            ),
        ]
        session.add_all(exercises)

        await session.commit()
        print(f"Módulo de ejemplo creado: '{module.title}' (A1) con 2 lecciones y 2 ejercicios.")


if __name__ == "__main__":
    asyncio.run(seed_curriculum())
