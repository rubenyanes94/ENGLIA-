"""Carga el examen de cada módulo de un nivel.

Uso:
    python -m app.scripts.seed_module_exams            # todos los de A1
    python -m app.scripts.seed_module_exams A1.M03     # solo ese módulo

Los exámenes revisados viven en exams_a1.json, y se cargan de ahí. Solo
se generan con el LLM los módulos que no están en el archivo. No es un
atajo para ahorrar llamadas: cada tanda generada salía con fallos que ni
la validación ni la verificación a ciegas detectaban (una clave que daba
por buena "wearing" como acentuada en la segunda sílaba, "No aparcar" en
vez de "No estacionar", un enunciado que preguntaba una cosa y unas
opciones que respondían otra). Todas se revisaron a mano. Generarlas de
nuevo en cada entorno daría a cada despliegue un examen distinto y sin
revisar, justo en lo que decide si un alumno avanza.

Idempotente: un módulo que ya tiene preguntas de examen se salta. Así se
puede relanzar tras un corte sin duplicar exámenes ni regenerar los que
ya están bien. Para rehacer el examen de un módulo hay que borrar antes
sus ejercicios de examen: regenerarlo en silencio dejaría huérfanas las
convocatorias que ya hicieron los alumnos.
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.exam_generation import ExamQuestion, generate_module_exam
from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel, Descriptor, Exercise, Module
from app.services.module_exam import list_exam_exercises


REVIEWED_EXAMS = Path(__file__).with_name("exams_a1.json")


def load_reviewed_exams() -> dict[str, list[ExamQuestion]]:
    if not REVIEWED_EXAMS.exists():
        return {}
    data = json.loads(REVIEWED_EXAMS.read_text(encoding="utf-8"))
    return {code: [ExamQuestion(**question) for question in questions] for code, questions in data.items()}


async def seed_module_exams(level_code: str = "A1", only: list[str] | None = None) -> None:
    async with AsyncSessionLocal() as session:
        query = (
            select(Module)
            .join(CEFRLevel)
            .options(selectinload(Module.lessons))
            .where(CEFRLevel.code == level_code)
            .order_by(Module.order)
        )
        if only:
            query = query.where(Module.code.in_(only))
        modules = list((await session.execute(query)).scalars().all())

        descriptor_rows = list((await session.execute(select(Descriptor))).scalars())
        statements = {d.code: d.statement_es for d in descriptor_rows}
        skills = {d.code: d.skill for d in descriptor_rows}

        reviewed = load_reviewed_exams()
        created = 0
        for module in modules:
            if await list_exam_exercises(session, module.id):
                print(f"  {module.code} — ya tiene examen, se salta.")
                continue
            if not module.lessons:
                # Los ejercicios cuelgan de una lección. Sin lección no hay
                # dónde guardarlos; se avisa en vez de fallar toda la tanda.
                print(f"  {module.code} — sin lección donde guardar el examen, se salta.")
                continue

            if module.code in reviewed:
                questions = reviewed[module.code]
                print(f"  {module.code} {module.title_es!r} · examen revisado", flush=True)
            else:
                print(f"  {module.code} {module.title_es!r} · generando (SIN REVISAR)...", flush=True)
                try:
                    questions = await generate_module_exam(module, statements, skills)
                except ValueError as exc:
                    print(f"    ✗ {exc}")
                    continue

            lesson = min(module.lessons, key=lambda lesson: lesson.order)
            for question in questions:
                session.add(
                    Exercise(
                        lesson_id=lesson.id,
                        exercise_type="multiple_choice",
                        stage="exam",
                        descriptor_codes=[question.descriptor_code],
                        prompt=question.prompt,
                        answer_key={"correct": question.correct, "options": question.options},
                    )
                )
            await session.commit()
            created += 1
            print(f"    ✓ {len(questions)} preguntas")

        print(f"\nListo: {created} examen(es) nuevo(s).")


if __name__ == "__main__":
    asyncio.run(seed_module_exams(only=sys.argv[1:] or None))
