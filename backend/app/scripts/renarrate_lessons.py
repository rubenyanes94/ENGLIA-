"""Vuelve a narrar con las voces ACTUALES todas las lecciones que ya
tienen guión.

Uso:
    python -m app.scripts.renarrate_lessons

Por qué existe como script propio y no como un flag de
seed_a1_lessons.py: aquel es idempotente a propósito (salta lo que ya
está hecho) para poder relanzarlo sin miedo tras un corte. Lo que hace
falta al cambiar de voz es justo lo contrario — rehacer audio que YA
existe — y mezclar las dos intenciones en un script convertiría "volver
a lanzar la siembra" en una operación destructiva por accidente.

No toca Ollama ni los guiones: reusa el texto tal cual está en la base
de datos y solo pasa Piper por encima. Cambiar de voz no debe reescribir
la lección — el guión de A1.M01 está escrito a mano (ver
lesson_scripts_a1.py) y regenerarlo sería perderlo.

El audio anterior se borra DESPUÉS de guardar el nuevo, nunca antes: si
la síntesis falla a mitad, el alumno se queda con la narración vieja en
vez de con una lección muda.
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.media.tts import get_wav_duration_seconds, synthesize_bilingual_to_wav
from app.media.storage import delete_lesson_audio, save_lesson_audio
from app.models import Lesson, Module
from app.repositories import lesson_repository


def describe_voices() -> list[str]:
    """Qué voces se van a usar DE VERDAD, según el motor activo.

    Antes esto imprimía siempre las rutas de Piper, con lo que la primera
    narración con Magpie anunció "es_MX-ald-medium" mientras sintetizaba
    con Diego. Un script que informa de una voz y usa otra es la forma
    más fácil de publicar el audio equivocado sin enterarse — por eso el
    motor manda aquí, no una suposición.
    """
    if settings.tts_provider == "magpie":
        return [
            f"Motor:        magpie (NVIDIA, remoto)",
            f"Voz español:  {settings.magpie_voice_es}",
            f"Voz inglés:   {settings.magpie_voice_en}",
        ]
    return [
        "Motor:        piper (local)",
        f"Voz español:  {settings.tts_voice_model_path_es.rsplit('/', 1)[-1].removesuffix('.onnx')}",
        f"Voz inglés:   {settings.tts_voice_model_path.rsplit('/', 1)[-1].removesuffix('.onnx')}",
    ]


async def renarrate_lessons(module_codes: list[str] | None = None) -> None:
    async with AsyncSessionLocal() as session:
        query = (
            select(Lesson)
            .join(Module)
            .options(selectinload(Lesson.module))
            .where(Lesson.script.isnot(None))
            .order_by(Module.order, Lesson.order)
        )
        if module_codes:
            query = query.where(Module.code.in_(module_codes))

        lessons = list((await session.execute(query)).scalars().all())

        if not lessons:
            print("No hay lecciones con guión que narrar.")
            return

        for line in describe_voices():
            print(line)
        print(f"{len(lessons)} lección(es) a re-narrar.\n")

        for index, lesson in enumerate(lessons, start=1):
            code = lesson.module.code or lesson.module.title
            print(f"  [{index}/{len(lessons)}] {code} — {lesson.title!r} · narrando...", flush=True)

            wav_bytes = await synthesize_bilingual_to_wav(lesson.script)
            duration = get_wav_duration_seconds(wav_bytes)

            previous_audio_url = lesson.audio_url
            audio_url = save_lesson_audio(lesson.id, wav_bytes)
            await lesson_repository.set_narration(session, lesson, lesson.script, audio_url, duration)
            if previous_audio_url:
                delete_lesson_audio(previous_audio_url)

            print(f"        ✓ {duration:.0f}s · {audio_url}\n", flush=True)

        print(f"Listo. {len(lessons)} narración(es) regenerada(s).")


if __name__ == "__main__":
    # Sin argumentos re-narra todo; con ellos, solo esos módulos
    # (ej. `python -m app.scripts.renarrate_lessons A1.M01`), útil para
    # probar una voz nueva en una sola lección antes de aplicarla a todas.
    asyncio.run(renarrate_lessons(sys.argv[1:] or None))
