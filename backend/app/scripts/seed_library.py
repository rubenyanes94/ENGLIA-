"""Carga los cursos de la Biblioteca desde library_courses.json.

Uso:
    python -m app.scripts.seed_library

Actualiza los cursos que ya existen (por slug) en vez de saltárselos:
el archivo es la fuente de verdad del contenido, y corregir una frase
clave ahí tiene que llegar a la base de datos al volver a cargarlo. No
borra cursos que ya no estén en el archivo, porque tienen progreso de
alumnos colgando.
"""

import asyncio
import json
from pathlib import Path

from app.core.db import AsyncSessionLocal
from app.models import FlashCourse
from app.repositories import flash_course_repository

CONTENT = Path(__file__).with_name("library_courses.json")
FIELDS = (
    "title", "title_es", "description_es", "category", "icon", "recommended_level", "duration_minutes",
    "communicative_objectives", "key_phrases", "scenarios", "tutor_config", "l1_interference",
)


def validate(courses: list[dict]) -> None:
    """Falla antes de tocar la base de datos si el archivo tiene algo que
    rompería la Biblioteca o el tutor en tiempo de ejecución."""
    slugs = [course["slug"] for course in courses]
    assert len(slugs) == len(set(slugs)), "hay slugs repetidos"
    scenario_ids: list[str] = []
    for course in courses:
        for field in ("slug", *FIELDS):
            assert field in course, f"{course.get('slug')}: falta '{field}'"
        assert course["scenarios"], f"{course['slug']}: no tiene escenarios"
        for scenario in course["scenarios"]:
            for field in ("id", "title", "prompt", "success_criteria", "tutor_role"):
                assert scenario.get(field), f"{course['slug']}: escenario sin '{field}'"
            scenario_ids.append(scenario["id"])
        for phrase in course["key_phrases"]:
            assert phrase.get("en") and phrase.get("es"), f"{course['slug']}: frase clave incompleta"
    # Ids únicos en TODA la Biblioteca: el chat busca la tarea dentro del
    # curso de la sesión, pero el progreso y los eventos solo guardan el id.
    assert len(scenario_ids) == len(set(scenario_ids)), "hay ids de escenario repetidos entre cursos"


async def seed_library() -> None:
    courses = json.loads(CONTENT.read_text(encoding="utf-8"))
    validate(courses)

    async with AsyncSessionLocal() as session:
        created = updated = 0
        for order, data in enumerate(courses, start=1):
            course = await flash_course_repository.get_by_slug(session, data["slug"])
            if course is None:
                course = FlashCourse(slug=data["slug"])
                session.add(course)
                created += 1
            else:
                updated += 1
            for field in FIELDS:
                setattr(course, field, data[field])
            course.order = order
        await session.commit()
        print(f"Biblioteca: {created} curso(s) nuevo(s), {updated} actualizado(s).")


if __name__ == "__main__":
    asyncio.run(seed_library())
