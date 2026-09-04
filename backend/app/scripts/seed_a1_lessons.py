"""Genera y narra una lección introductoria por cada módulo de A1.

Uso:
    python -m app.scripts.seed_a1_lessons

Va en DOS FASES, y eso NO es un capricho de organización: es lo que hace
que quepa en memoria. El modelo de Ollama ocupa ~500MB residentes y Piper
necesita cargar DOS modelos ONNX (voz española + inglesa) encima. Con los
dos vivos a la vez, el proceso muere ("Terminated") a mitad de la tanda —
pasó de verdad. Separando las fases, el pico de memoria es el MAYOR de
los dos, no la suma:

  Fase 1 — Ollama escribe los 10 guiones (explicación en español con los
           ejemplos en inglés entre [[corchetes]]) y se guardan en la
           lección. El tema de cada uno sale del propio currículo del
           módulo (objetivos + gramática + chunks), no de una lista
           escrita a mano.
  · Entre fases se DESCARGA el modelo de Ollama de la memoria.
  Fase 2 — Piper narra cada guión con las dos voces y se guarda el WAV.

Idempotente en las dos fases: un módulo que ya tenga lección se salta en
la fase 1, y una lección que ya tenga audio se salta en la fase 2. Así,
si esto se corta por lo que sea, relanzarlo retoma donde quedó en vez de
rehacerlo todo.
"""

import asyncio
import json
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.lesson_narration import generate_lesson_script
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.media.piper_tts import get_wav_duration_seconds, synthesize_bilingual_to_wav
from app.media.storage import save_lesson_audio
from app.models import CEFRLevel, Lesson, Module
from app.repositories import lesson_repository, persona_repository


def unload_llm() -> None:
    """Saca el modelo de la memoria de Ollama antes de arrancar Piper.

    `keep_alive: 0` es la forma documentada de pedirle a Ollama que
    descargue un modelo ya. Sin esto, el modelo se queda residente hasta
    que expire OLLAMA_KEEP_ALIVE (1h en nuestro compose) y le roba a
    Piper la memoria que necesita.

    No lanza si falla: si no se puede descargar, la fase 2 igual lo
    intenta — y si no cabe, fallará ahí con un error claro, no aquí.
    """
    base = settings.llm_base_url.rsplit("/v1", 1)[0]
    try:
        request = urllib.request.Request(
            f"{base}/api/generate",
            data=json.dumps({"model": settings.llm_model, "keep_alive": 0}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=30).read()
        print("  · modelo de Ollama descargado de memoria\n")
    except Exception as exc:  # noqa: BLE001 — informativo, no crítico
        print(f"  · aviso: no se pudo descargar el modelo de Ollama ({exc})\n")


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

        total = len(modules)
        print(f"{total} módulos en A1.\n")

        # ---------- Fase 1: guiones (solo Ollama en memoria) ----------
        print("FASE 1 — Guiones\n")
        written = 0
        for module in modules:
            if module.lessons:
                print(f"  [{module.order}/{total}] {module.code} — ya tiene lección, se salta.")
                continue

            topic = build_topic(module)
            print(f"  [{module.order}/{total}] {module.code} {module.title!r} · escribiendo...", flush=True)
            script = await generate_lesson_script(topic, "A1", persona)

            lesson = await lesson_repository.create(
                session,
                module.id,
                title=f"Introducción: {module.title_es}",
                content={"type": "narrated", "topic": topic},
                order=1,
            )
            # Se guarda el guión YA, sin audio: si la fase 2 se corta, el
            # trabajo del LLM (lo más caro) no se pierde.
            lesson.script = script
            await session.commit()

            written += 1
            print(f"        ✓ {len(script)} caracteres\n", flush=True)

        print(f"Fase 1 lista: {written} guiones nuevos.\n")

        unload_llm()

        # ---------- Fase 2: audio (solo Piper en memoria) ----------
        print("FASE 2 — Narración\n")
        pending = (
            (
                await session.execute(
                    select(Lesson)
                    .join(Module)
                    .where(Module.level_id == level.id, Lesson.script.isnot(None), Lesson.audio_url.is_(None))
                    .order_by(Module.order)
                )
            )
            .scalars()
            .all()
        )

        narrated = 0
        for index, lesson in enumerate(pending, start=1):
            print(f"  [{index}/{len(pending)}] {lesson.title!r} · narrando (voz ES + EN)...", flush=True)
            wav_bytes = await synthesize_bilingual_to_wav(lesson.script)
            duration = get_wav_duration_seconds(wav_bytes)
            audio_url = save_lesson_audio(lesson.id, wav_bytes)
            await lesson_repository.set_narration(session, lesson, lesson.script, audio_url, duration)

            narrated += 1
            print(f"        ✓ {duration:.0f}s de audio\n", flush=True)

        print(f"Listo. {written} guiones y {narrated} narraciones nuevas.")


if __name__ == "__main__":
    asyncio.run(seed_a1_lessons())
