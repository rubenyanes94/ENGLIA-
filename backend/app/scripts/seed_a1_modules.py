"""Siembra los 8 módulos que distribuyen la certificación A1 (según lo
pedido: 8 módulos, 80-150h de aprendizaje guiado en total).

Uso:
    python -m app.scripts.seed_a1_modules

Idempotente por título (dentro de A1): si un módulo con ese título ya
existe, no lo duplica ni lo toca — así no pisa contenido/horas que un
admin ya haya ajustado a mano vía PATCH /admin/modules/{id}.

AVISO: los TÍTULOS y el reparto de horas son un currículo de ejemplo
razonable (temas típicos de A1), no un plan de estudios oficial —
pénsalo como un punto de partida para que el bloqueo secuencial y las
horas de certificación tengan 8 módulos reales con los que probarse,
no como contenido pedagógico definitivo.
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel, Module

# 8 módulos, 100h en total (dentro del rango 80-150h de A1) — el peso en
# horas de cada uno es parejo a propósito (12.5h c/u); un admin puede
# rebalancearlo después según qué tan denso resulte cada tema en la práctica.
A1_MODULES = [
    {"title": "Presentarse", "skill_focus": "speaking", "order": 1, "estimated_hours": 12.5},
    {"title": "Mi familia y yo", "skill_focus": "speaking", "order": 2, "estimated_hours": 12.5},
    {"title": "Rutina diaria", "skill_focus": "reading", "order": 3, "estimated_hours": 12.5},
    {"title": "Comida y bebida", "skill_focus": "listening", "order": 4, "estimated_hours": 12.5},
    {"title": "La ciudad: direcciones y transporte", "skill_focus": "listening", "order": 5, "estimated_hours": 12.5},
    {"title": "De compras", "skill_focus": "reading", "order": 6, "estimated_hours": 12.5},
    {"title": "El clima y los planes", "skill_focus": "writing", "order": 7, "estimated_hours": 12.5},
    {"title": "Experiencias pasadas: el pasado simple", "skill_focus": "writing", "order": 8, "estimated_hours": 12.5},
]


async def seed_a1_modules() -> None:
    async with AsyncSessionLocal() as session:
        level_result = await session.execute(select(CEFRLevel).where(CEFRLevel.code == "A1"))
        level = level_result.scalars().first()
        if level is None:
            print("No existe el nivel A1 todavía — corre antes `python -m app.scripts.seed_cefr_levels`.")
            return

        existing_result = await session.execute(select(Module.title).where(Module.level_id == level.id))
        existing_titles = {row[0] for row in existing_result.all()}

        new_modules = [
            Module(level_id=level.id, **data) for data in A1_MODULES if data["title"] not in existing_titles
        ]

        if not new_modules:
            print("Los 8 módulos de A1 ya existían. Nada que insertar.")
            return

        session.add_all(new_modules)
        await session.commit()

        titles = ", ".join(f"{m.order}. {m.title}" for m in sorted(new_modules, key=lambda m: m.order))
        total_hours = sum(m.estimated_hours for m in new_modules)
        print(f"Insertados {len(new_modules)} módulos nuevos en A1 ({total_hours}h): {titles}")


if __name__ == "__main__":
    asyncio.run(seed_a1_modules())
