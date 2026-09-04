"""Genera y narra una lección introductoria por cada módulo de A1.

Uso:
    python -m app.scripts.seed_a1_lessons

Para cada módulo sin lecciones:
  1. Arma el TEMA a partir del propio currículo del módulo (objetivos
     comunicativos + foco gramatical), no de una lista escrita a mano —
     así la lección habla exactamente de lo que ese módulo enseña.
  2. Ollama escribe el guión: explicación en español con los ejemplos en
     inglés entre [[corchetes]] (ver agents/lesson_narration.py).
  3. Piper lo narra con DOS voces — española para la explicación, inglesa
     para los ejemplos (ver media/piper_tts.py).
  4. Guarda el WAV y la lección.

Idempotente: un módulo que ya tenga lecciones se salta. Es importante,
porque generar las diez tarda ~15-20 min en CPU y no queremos rehacerlo
por relanzar el script.

LENTO a propósito de anunciar: cada módulo son una llamada al LLM y una
síntesis de audio, ambas en CPU. Va imprimiendo el avance módulo a módulo.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.lesson_narration import generate_lesson_script
from app.core.db import AsyncSessionLocal
from app.media.piper_tts import get_wav_duration_seconds, synthesize_bilingual_to_wav
from app.media.storage import save_lesson_audio
from app.models import CEFRLevel, Module
from app.repositories import lesson_repository, persona_repository


def build_topic(module: Module) -> str:
    """El tema que se le pasa al LLM, construido desde el currículo real
    del módulo. Se limitan objetivos y gramática a los primeros para no
    inflar el prompt: con un modelo pequeño, un prompt largo produce
    guiones peores, no mejores."""
    objectives = "; ".join(module.communicative_objectives[:3])
    grammar = "; ".join((module.grammar or {}).get("focus", [])[:3])
    chunks = ", ".join((module.lexis or {}).get("chunks", [])[:3])

    parts = [f'"{module.title_es}" ({module.title})']
    if objectives:
        parts.append(f"El alumno debe aprender a: {objectives}")
    if grammar:
        parts.append(f"Estructuras clave: {grammar}")
    if chunks:
        parts.append(f"Frases que debe repetir en inglés: {chunks}")
    return ". ".join(parts)


async def seed_a1_lessons() -> None:
    async with AsyncSessionLocal() as session:
        level = (await session.execute(select(CEFRLevel).where(CEFRLevel.code == "A1"))).scalars().first()
        if level is None:
            print("No existe el nivel A1 — corre antes `python -m app.scripts.seed_cefr_levels`.")
            return

        persona = await persona_repository.get_active_persona_by_level_code(session, "A1")
        if persona is None:
            print("No hay tutor activo para A1 — corre antes `python -m app.scripts.seed_agent_personas`.")
            return

        result = await session.execute(
            select(Module)
            .options(selectinload(Module.lessons))
            .where(Module.level_id == level.id)
            .order_by(Module.order)
        )
        modules = list(result.scalars().all())

        print(f"{len(modules)} módulos en A1. Generando lección para los que no tengan...\n")

        created = 0
        for module in modules:
            if module.lessons:
                print(f"  [{module.order}/{len(modules)}] {module.code} — ya tiene lección, se salta.")
                continue

            topic = build_topic(module)
            print(f"  [{module.order}/{len(modules)}] {module.code} {module.title!r}")
            print("        · generando guión...", flush=True)
            script = await generate_lesson_script(topic, "A1", persona)

            print("        · narrando (voz ES + EN)...", flush=True)
            wav_bytes = await synthesize_bilingual_to_wav(script)
            duration = get_wav_duration_seconds(wav_bytes)

            lesson = await lesson_repository.create(
                session,
                module.id,
                title=f"Introducción: {module.title_es}",
                content={"type": "narrated", "topic": topic},
                order=1,
            )
            audio_url = save_lesson_audio(lesson.id, wav_bytes)
            await lesson_repository.set_narration(session, lesson, script, audio_url, duration)

            created += 1
            print(f"        ✓ {duration:.0f}s de audio · {len(script)} caracteres de guión\n", flush=True)

        print(f"Listo. {created} lecciones nuevas generadas.")


if __name__ == "__main__":
    asyncio.run(seed_a1_lessons())
