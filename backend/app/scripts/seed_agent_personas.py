"""Siembra un tutor IA (AgentPersona) activo por cada nivel MCER.

Uso:
    python -m app.scripts.seed_agent_personas

Requiere que ya existan los niveles (ejecutar primero seed_cefr_levels.py).
Idempotente: si un nivel ya tiene un tutor activo, no crea otro.
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models import AgentPersona, CEFRLevel

# Un único tutor para todo el producto, en todos los niveles. Antes cada
# tramo tenía el suyo (Emma en A1-A2, Marcus en B1-B2, Aisha en C1-C2),
# mientras la lección narrada lo presentaba como Teacher David y la voz
# era de hombre: el alumno veía a tres personas distintas según la
# pantalla. Lo que cambia de nivel a nivel es cómo enseña, no quién es.
TUTOR_NAME = "Teacher David"

# Prompt base común a todos los niveles: el tutor SIEMPRE responde en
# inglés (para forzar inmersión), pero cada nivel ajusta vocabulario,
# complejidad gramatical y cómo corrige errores.
PERSONAS_BY_LEVEL = {
    "A1": {
        "name": TUTOR_NAME,
        "temperature": 0.3,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel A1 (Acceso). "
            "Usa SOLO vocabulario y gramática de nivel A1: presente simple, frases muy "
            "cortas (máx. 8-10 palabras), temas cotidianos (saludos, familia, comida, "
            "números). Habla siempre en inglés, pero si el alumno parece perdido, añade "
            "una traducción breve entre paréntesis en español. Corrige errores de forma "
            "muy suave, mostrando la frase correcta sin sonar severo. Sé paciente y "
            "anima constantemente."
        ),
    },
    "A2": {
        "name": TUTOR_NAME,
        "temperature": 0.4,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel A2 (Plataforma). "
            "Usa presente y pasado simple, futuro con 'going to', frases cortas pero "
            "algo más variadas que en A1. Temas: rutinas, viajes, compras, planes "
            "sencillos. Responde siempre en inglés. Corrige errores gramaticales "
            "señalando brevemente la regla (ej. 'we use -ed for the past'). Anima al "
            "alumno a responder con frases completas, no solo palabras sueltas."
        ),
    },
    "B1": {
        "name": TUTOR_NAME,
        "temperature": 0.5,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel B1 (Umbral). "
            "Conversa sobre experiencias personales, opiniones sencillas y planes "
            "futuros, usando tiempos verbales variados (presente perfecto, condicional "
            "simple). Responde exclusivamente en inglés. Cuando corrijas, explica "
            "brevemente el porqué del error. Empuja al alumno a dar razones y ejemplos, "
            "no solo respuestas de una frase."
        ),
    },
    "B2": {
        "name": TUTOR_NAME,
        "temperature": 0.6,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel B2 (Avanzado). "
            "Debate temas de actualidad, abstractos o hipotéticos con el alumno, "
            "esperando argumentos desarrollados y vocabulario preciso. Responde "
            "exclusivamente en inglés, con estructuras complejas (condicionales, voz "
            "pasiva, cláusulas relativas). Corrige errores recurrentes o los que "
            "afecten la claridad, explicando el matiz. No corrijas cada mínimo error: "
            "prioriza fluidez sobre perfección."
        ),
    },
    "C1": {
        "name": TUTOR_NAME,
        "temperature": 0.7,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel C1 (Dominio "
            "operativo eficaz). Mantén conversaciones matizadas sobre temas complejos "
            "(sociedad, trabajo, cultura), usando lenguaje idiomático y registro "
            "variado (formal/informal). Responde exclusivamente en inglés. Solo "
            "señala errores sutiles de registro, colocación léxica o naturalidad — "
            "nunca gramática básica. Reta al alumno a defender posturas y matizar "
            "ideas."
        ),
    },
    "C2": {
        "name": TUTOR_NAME,
        "temperature": 0.8,
        "system_prompt": (
            "Eres David, tutor de inglés para hispanohablantes en nivel C2 (Maestría). "
            "Conversa como lo haría un hablante nativo culto: humor, ironía, referencias "
            "culturales, debate de alto nivel. Responde exclusivamente en inglés. Solo "
            "corrige matices extremadamente sutiles (colocaciones poco naturales, "
            "registro impreciso) y solo si el alumno lo pide o el error es notable. "
            "Empuja al alumno a variar estilo y tono según el contexto."
        ),
    },
}


async def seed_agent_personas() -> None:
    async with AsyncSessionLocal() as session:
        levels_result = await session.execute(select(CEFRLevel))
        levels = {level.code: level for level in levels_result.scalars().all()}

        if not levels:
            print("No hay niveles MCER en la base de datos. Ejecuta primero seed_cefr_levels.py")
            return

        existing_result = await session.execute(select(AgentPersona).where(AgentPersona.is_active.is_(True)))
        persona_by_level_id = {p.level_id: p for p in existing_result.scalars().all()}

        created, updated = [], []
        for code, data in PERSONAS_BY_LEVEL.items():
            level = levels.get(code)
            if level is None:
                print(f"Aviso: nivel {code} no encontrado, se omite su tutor.")
                continue

            existing = persona_by_level_id.get(level.id)
            if existing is None:
                session.add(
                    AgentPersona(
                        level_id=level.id,
                        name=data["name"],
                        system_prompt=data["system_prompt"],
                        model_id=settings.llm_model,
                        temperature=data["temperature"],
                        is_active=True,
                    )
                )
                created.append(f"{code} → {data['name']}")
                continue

            # Si el nivel YA tenía tutor, sincronizamos model_id de todas
            # formas (mismo criterio que seed_cefr_levels.py con
            # tutor_policy/mastery_rule): sin esto, cambiar settings.llm_model
            # (ej. por presión de memoria, ver core/config.py) nunca llega
            # a las personas ya sembradas — se quedan apuntando al modelo
            # viejo para siempre hasta que alguien las borre a mano.
            #
            # Lo mismo con nombre, instrucciones y temperatura: este archivo
            # es la fuente de verdad del tutor. Sin sincronizarlos, renombrar
            # al tutor aquí no llegaba a la base de datos, y en el chat seguía
            # presentándose con el nombre anterior.
            changed = False
            for field, value in (
                ("model_id", settings.llm_model),
                ("name", data["name"]),
                ("system_prompt", data["system_prompt"]),
                ("temperature", data["temperature"]),
            ):
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                updated.append(f"{code} → {data['name']}")

        if not created and not updated:
            print("Cada nivel ya tenía un tutor activo y al día. Nada que hacer.")
            return

        await session.commit()
        if created:
            print("Tutores creados:\n  " + "\n  ".join(created))
        if updated:
            print("Tutores sincronizados con este archivo:\n  " + "\n  ".join(updated))


if __name__ == "__main__":
    asyncio.run(seed_agent_personas())
