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
# concreto, partiendo de haber certificado el anterior. Valores tomados
# del documento de diseño curricular MCER § 2.1 (alineados con
# estimaciones Cambridge/ALTE), no una estimación propia.
CEFR_LEVELS = [
    {
        "code": "A1",
        "name": "Acceso",
        "order": 1,
        "target_hours_min": 90,
        "target_hours_max": 100,
        "description": (
            "Usuario básico. Comprende y utiliza expresiones cotidianas de uso "
            "muy frecuente, así como frases sencillas para satisfacer necesidades "
            "inmediatas. Puede presentarse y presentar a otros."
        ),
        # level_policy del documento de currículo (§ nivel A1, cabecera de
        # MODULES A1): heredado por todos los módulos del nivel salvo
        # override explícito en su propio tutor_config.
        "tutor_policy": {
            "tutor_language_ceiling": {
                "allowed": [
                    "present_simple",
                    "present_continuous",
                    "past_simple_common",
                    "going_to",
                    "can",
                    "imperatives",
                    "there_is_are",
                ],
                "forbidden": [
                    "present_perfect",
                    "conditionals",
                    "passive_voice",
                    "reported_speech",
                    "relative_clauses",
                    "phrasal_verbs_idiomatic",
                ],
            },
            "tutor_speech_rate": "slow",
            "max_new_lexis_per_session": 8,
            "l1_support": (
                "Se permite español para instrucciones de tarea y aclaración de "
                "significado. Nunca para modelar la respuesta esperada."
            ),
            "correction_hierarchy": [
                "Error que rompe comunicación → corrección inmediata",
                "Error del módulo activo → recast sin interrumpir",
                "Error de módulo anterior → registrar, corregir al cierre",
                "Error por encima del nivel → ignorar por completo",
            ],
        },
        # mastery_rule del documento DESCRIPTORS A1: regla uniforme con la
        # que se calcula descriptor_mastery para TODOS los descriptores del
        # nivel (ver descriptor_evidence_repository.get_mastery_for_level).
        "mastery_rule": {
            "threshold": 0.8,
            "evidence_required": 3,
            "conditions": [
                "Ejecuciones en contextos distintos",
                "Ejecuciones en sesiones distintas",
                "Sin andamiaje directo del tutor en al menos una de ellas",
            ],
        },
    },
    {
        "code": "A2",
        "name": "Plataforma",
        "target_hours_min": 90,
        "target_hours_max": 110,
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
        "target_hours_max": 180,
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
        "target_hours_min": 180,
        "target_hours_max": 200,
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
        "target_hours_min": 200,
        "target_hours_max": 220,
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
        "target_hours_min": 250,
        "target_hours_max": 300,
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
            # nivel YA existía sincronizamos target_hours_* y tutor_policy
            # de todas formas — es la única forma de que niveles sembrados
            # ANTES de que existiera cada campo terminen con los valores
            # reales en vez del server_default genérico de su migración.
            changed = False
            if existing.target_hours_min != data["target_hours_min"] or existing.target_hours_max != data["target_hours_max"]:
                existing.target_hours_min = data["target_hours_min"]
                existing.target_hours_max = data["target_hours_max"]
                changed = True
            new_policy = data.get("tutor_policy")
            if new_policy and existing.tutor_policy != new_policy:
                existing.tutor_policy = new_policy
                changed = True
            new_mastery_rule = data.get("mastery_rule")
            if new_mastery_rule and existing.mastery_rule != new_mastery_rule:
                existing.mastery_rule = new_mastery_rule
                changed = True
            if changed:
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
