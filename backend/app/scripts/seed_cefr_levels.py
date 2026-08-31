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

CEFR_LEVELS = [
    {
        "code": "A1",
        "name": "Acceso",
        "order": 1,
        "description": (
            "Usuario básico. Comprende y utiliza expresiones cotidianas de uso "
            "muy frecuente, así como frases sencillas para satisfacer necesidades "
            "inmediatas. Puede presentarse y presentar a otros."
        ),
    },
    {
        "code": "A2",
        "name": "Plataforma",
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
        "description": (
            "Usuario competente. Comprende con facilidad prácticamente todo lo "
            "que oye o lee. Puede expresarse espontáneamente, con gran fluidez y "
            "precisión, distinguiendo matices sutiles de significado."
        ),
    },
]


async def seed_cefr_levels() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CEFRLevel.code))
        existing_codes = {row[0] for row in result.all()}

        new_levels = [CEFRLevel(**data) for data in CEFR_LEVELS if data["code"] not in existing_codes]

        if not new_levels:
            print("Los 6 niveles MCER ya existían. Nada que insertar.")
            return

        session.add_all(new_levels)
        await session.commit()

        codes = ", ".join(level.code for level in new_levels)
        print(f"Insertados {len(new_levels)} niveles nuevos: {codes}")


if __name__ == "__main__":
    asyncio.run(seed_cefr_levels())
