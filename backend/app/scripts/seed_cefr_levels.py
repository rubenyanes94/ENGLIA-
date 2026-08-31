"""Siembra los 6 niveles fijos del Marco Común Europeo de Referencia.

Uso:
    python -m app.scripts.seed_cefr_levels

Es idempotente: si un nivel (por su "code") ya existe, no lo duplica.
Se puede ejecutar tantas veces como haga falta sin miedo.
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel

# target_hours_* son horas de aprendizaje GUIADO por nivel (no
# acumuladas desde cero) — cuánto dura certificarse EN ese nivel
# concreto, partiendo de haber certificado el anterior. Los rangos de
# A1 vienen de un requerimiento explícito (80-150h); A2-C2 son
# estimaciones de referencia (a mayor nivel, más horas) — ajústalas si
# tu institución maneja otros números, no son un estándar oficial fijo.
CEFR_LEVELS = [
    {
        "code": "A1",
        "name": "Acceso",
        "order": 1,
        "target_hours_min": 80,
        "target_hours_max": 150,
        "description": (
            "Usuario básico. Comprende y utiliza expresiones cotidianas de uso "
            "muy frecuente, así como frases sencillas para satisfacer necesidades "
            "inmediatas. Puede presentarse y presentar a otros."
        ),
    },
    {
        "code": "A2",
        "name": "Plataforma",
        "target_hours_min": 100,
        "target_hours_max": 180,
        "order": 2,
        "description": (
            "Usuario básico. Comprende frases y expresiones de uso frecuente "
            "relacionadas con áreas de experiencia relevantes (información "
            "personal y familiar, compras, geografía local, empleo)."
        ),
    },
    {
        "code": "B1",
        "name": "Umbral",
        "order": 3,
        "target_hours_min": 150,
        "target_hours_max": 250,
        "description": (
            "Usuario independiente. Comprende los puntos principales de textos "
            "claros sobre asuntos cotidianos. Sabe desenvolverse en la mayoría "
            "de situaciones que pueden surgir viajando por zonas de habla inglesa."
        ),
    },
    {
        "code": "B2",
        "name": "Avanzado",
        "order": 4,
        "target_hours_min": 200,
        "target_hours_max": 300,
        "description": (
            "Usuario independiente. Comprende las ideas principales de textos "
            "complejos, incluso de carácter técnico. Puede relacionarse con "
            "hablantes nativos con fluidez y espontaneidad."
        ),
    },
    {
        "code": "C1",
        "name": "Dominio operativo eficaz",
        "order": 5,
        "target_hours_min": 250,
        "target_hours_max": 350,
        "description": (
            "Usuario competente. Comprende una amplia variedad de textos extensos "
            "y con cierto nivel de exigencia, reconociendo sentidos implícitos. "
            "Se expresa de forma fluida y espontánea sin buscar de forma muy "
            "evidente las expresiones."
        ),
    },
    {
        "code": "C2",
        "name": "Maestría",
        "order": 6,
        "target_hours_min": 300,
        "target_hours_max": 450,
        "description": (
            "Usuario competente. Comprende con facilidad prácticamente todo lo "
            "que oye o lee. Puede expresarse espontáneamente, con gran fluidez y "
            "precisión, distinguiendo matices sutiles de significado."
        ),
    },
]


async def seed_cefr_levels() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CEFRLevel))
        existing_by_code = {level.code: level for level in result.scalars().all()}

        new_levels = []
        updated_codes = []

        for data in CEFR_LEVELS:
            existing = existing_by_code.get(data["code"])
            if existing is None:
                new_levels.append(CEFRLevel(**data))
                continue

            # A diferencia de la primera versión de este script, si el
            # nivel YA existía sincronizamos target_hours_* de todas
            # formas — es la única forma de que niveles sembrados ANTES
            # de que existiera este campo (los 6 originales) terminen
            # con las horas reales en vez de el server_default genérico
            # de la migración (80/150 para los seis, sin distinguir).
            if existing.target_hours_min != data["target_hours_min"] or existing.target_hours_max != data["target_hours_max"]:
                existing.target_hours_min = data["target_hours_min"]
                existing.target_hours_max = data["target_hours_max"]
                updated_codes.append(data["code"])

        if new_levels:
            session.add_all(new_levels)

        if new_levels or updated_codes:
            await session.commit()

        if new_levels:
            print(f"Insertados {len(new_levels)} niveles nuevos: {', '.join(l.code for l in new_levels)}")
        if updated_codes:
            print(f"Horas de certificación sincronizadas en: {', '.join(updated_codes)}")
        if not new_levels and not updated_codes:
            print("Los 6 niveles MCER ya estaban al día. Nada que hacer.")


if __name__ == "__main__":
    asyncio.run(seed_cefr_levels())
