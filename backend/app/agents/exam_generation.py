"""Genera el examen de un módulo a partir de su currículo real.

Por qué hace falta: el módulo N+1 solo se desbloquea cuando el N está
completado, y "completado" sale de la nota de los ejercicios de examen.
Hasta ahora no había ni uno en la base de datos, así que ningún alumno
podía pasar del módulo 1 de ninguna forma.

Las preguntas son de opción múltiple a propósito, no abiertas: este
examen decide si el alumno avanza, y esa decisión tiene que corregirse
siempre igual. Una respuesta abierta calificada por un LLM puede aprobar
hoy lo que suspende mañana.

Los distractores salen de `l1_interference` del módulo cuando se puede.
Una pregunta cuyo error tentador es justo el que comete un
hispanohablante ("I have 25 years") mide lo que el módulo enseña; una
con distractores absurdos solo mide si el alumno sabe descartar
tonterías.
"""

import json
import logging
import math
import random
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm_client import ainvoke_serialized, get_llm
from app.core.config import settings
from app.models import Module

logger = logging.getLogger(__name__)

EXAM_QUESTION_COUNT = 8
OPTIONS_PER_QUESTION = 4

SYSTEM_PROMPT = """\
Eres un evaluador experto del MCER que escribe exámenes para hispanohablantes \
latinoamericanos que aprenden inglés. Devuelves SOLO JSON válido, sin texto \
alrededor y sin bloque markdown."""

USER_PROMPT = """\
Escribe el examen del módulo "{title_es}" ({title}), nivel {level_code}.

Lo que el módulo enseña:
- Objetivos: {objectives}
- Gramática: {grammar}
- Frases clave: {chunks}

Capacidades que se evalúan (usa EXACTAMENTE estos códigos):
{descriptors}

Errores típicos de un hispanohablante en este módulo (úsalos como distractores):
{interference}

Reglas:
- Exactamente {count} preguntas de opción múltiple, repartidas entre las \
capacidades: no más de {max_per_code} preguntas por código.
- Cada pregunta tiene exactamente {options} opciones distintas y UNA sola correcta.
- Nivel {level_code}: frases cortas y vocabulario del módulo, nada más difícil.
- El enunciado va en español cuando pregunta cómo se dice algo \
("¿Cómo te presentas diciendo tu profesión?") y puede mostrar una frase en \
inglés con un hueco ("I ___ 25 years old.").
- Las opciones van en inglés.
- Nada de "todas las anteriores" ni "ninguna de las anteriores".
- Las opciones tienen que diferenciarse en algo más que mayúsculas o \
puntuación: la corrección no distingue mayúsculas, así que "Carlos" y \
"carlos" contarían las dos como correctas.
- NADA de pronunciación: ni acento, ni sílabas tónicas, ni sonidos, ni rimas. \
En un examen escrito no se pueden evaluar bien, y la pronunciación ya se \
practica con el micrófono de la lección.
- Siempre que se pueda, una de las opciones incorrectas es uno de los errores \
típicos de arriba.
- LAS OPCIONES INCORRECTAS TIENEN QUE SER INGLÉS INCORRECTO, no otra forma \
válida de decir lo mismo. Nunca pongas a la vez una contracción y su forma \
completa ("I'm" / "I am"), ni una respuesta corta y su versión larga \
("I'm 20." / "I'm 20 years old."): las dos son correctas.
- Si la pregunta admite varias respuestas naturales (saludos, despedidas), el \
enunciado da el contexto exacto para que solo una encaje ("Es de noche y te \
vas a dormir. ¿Qué dices?").
- {spanish_variety}

Formato:
{{"questions": [{{"descriptor_code": "A1.XX.00", "prompt": "...", \
"options": ["...", "...", "...", "..."], "correct": "..."}}]}}"""


VERIFY_PROMPT = """\
Eres profesor nativo de inglés revisando un examen para hispanohablantes de \
nivel A1. Para cada pregunta responde dos cosas:

1. "correct": TODAS las opciones que un profesor aceptaría como respuesta \
válida. Sé generoso: si una opción se puede defender razonablemente, inclúyela \
aunque haya otra mejor. Juzga cada opción por sí misma, no busques "la buena".

2. "giveaway": true si la pregunta se puede acertar copiando algo del enunciado \
sin saber inglés (ejemplo: "¿Qué palabra suena como en 'see'?" con la opción \
"see"). Una pregunta de comprensión que pide ENTENDER un texto en inglés no es \
regalada aunque la respuesta esté en ese texto.

{questions}

Formato: {{"answers": [{{"correct": ["texto exacto de la opción", ...], \
"giveaway": false}}, ...]}} — un objeto por pregunta, en el mismo orden."""


@dataclass
class ExamQuestion:
    descriptor_code: str
    prompt: str
    options: list[str]
    correct: str


# Destreza que se deja fuera del examen escrito. En la primera tanda, las
# preguntas de fonología fueron las que salieron mal, y de forma
# sistemática: una daba por buena "wearing" como palabra acentuada en la
# segunda sílaba (lo está en la primera), otra aceptaba solo "sunny" cuando
# "reading" y "wearing" también cumplían, y otra se respondía copiando el
# enunciado ("el sonido /ɪ/ como en 'sit'" -> "sit"). El verificador no las
# cazó porque el modelo se equivoca igual al resolverlas. Además, un acento
# no se puede oír en una pregunta escrita.
EXCLUDED_SKILLS = {"phonology"}

PHONOLOGY_PROMPT = re.compile(r"s[ií]laba|acento|t[óo]nica|sonido|pronunci|rima|\/[^/\s]{1,6}\/", re.IGNORECASE)


def exam_descriptor_codes(module: Module, skills: dict[str, str]) -> list[str]:
    """Los descriptores del módulo que se evalúan en el examen escrito."""
    return [code for code in module.descriptors if skills.get(code) not in EXCLUDED_SKILLS]


def max_questions_per_code(code_count: int) -> int:
    """Tope de preguntas por capacidad. Normalmente 2, para repartir el
    examen; más si el módulo tiene tan pocas capacidades evaluables que con
    2 no se llega a las preguntas necesarias (A1.M07 tiene 3: con tope 2
    saldrían 6 de 8)."""
    if code_count == 0:
        return EXAM_QUESTION_COUNT
    return max(MAX_QUESTIONS_PER_DESCRIPTOR, math.ceil(EXAM_QUESTION_COUNT / code_count))


def _format_context(module: Module, descriptor_statements: dict[str, str], codes: list[str]) -> dict:
    grammar = (module.grammar or {}).get("focus", [])
    chunks = (module.lexis or {}).get("chunks", [])
    interference = module.l1_interference or []
    return {
        "title": module.title,
        "title_es": module.title_es or module.title,
        "level_code": module.code.split(".", 1)[0] if module.code else "A1",
        "objectives": "; ".join(module.communicative_objectives) or "—",
        "grammar": "; ".join(grammar) or "—",
        "chunks": ", ".join(chunks) or "—",
        "descriptors": "\n".join(f"- {code}: {descriptor_statements.get(code, '')}" for code in codes),
        "interference": "\n".join(f'- "{item["error"]}" en vez de "{item["target"]}"' for item in interference)
        or "—",
        "count": EXAM_QUESTION_COUNT,
        "options": OPTIONS_PER_QUESTION,
        "max_per_code": max_questions_per_code(len(codes)),
    }


def _parse(raw: str) -> list[dict]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("la respuesta no contiene JSON")
    # strict=False acepta saltos de línea sueltos dentro de los textos. El
    # modelo los mete a veces en un enunciado largo, y con el parser
    # estricto se perdía la ronda entera por un carácter.
    data = json.loads(match.group(0), strict=False)
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError('falta la lista "questions"')
    return questions


MAX_QUESTIONS_PER_DESCRIPTOR = 2

# Cuántas preguntas de más se piden en cada ronda. Algunas no pasan los
# filtros, y pedir justo las que faltan obligaría a otra ronda casi siempre.
EXTRA_PER_ROUND = 4


def question_problems(question: dict, allowed_codes: list[str]) -> list[str]:
    """Problemas de forma de UNA pregunta. Lista vacía = se puede usar."""
    problems: list[str] = []
    prompt = str(question.get("prompt", "")).strip()
    options = question.get("options")
    correct = str(question.get("correct", "")).strip()
    code = str(question.get("descriptor_code", "")).strip()

    if len(prompt) < 10:
        problems.append("enunciado vacío o demasiado corto")
    if PHONOLOGY_PROMPT.search(prompt):
        problems.append("es una pregunta de pronunciación, y esas no van en el examen escrito")
    if code not in allowed_codes:
        problems.append(f"el código {code!r} no es de este módulo")
    if not isinstance(options, list) or len(options) != OPTIONS_PER_QUESTION:
        problems.append(f"no tiene exactamente {OPTIONS_PER_QUESTION} opciones")
        return problems

    # Se comparan en minúsculas porque así corrige grade_closed_exercise.
    # Opciones que solo cambian en mayúsculas ("Carlos" / "carlos")
    # puntuarían TODAS como correctas.
    normalized = [str(option).strip().lower() for option in options]
    if any(not option for option in normalized) or len(set(normalized)) != len(normalized):
        problems.append("hay opciones vacías o que solo cambian en mayúsculas")
    if correct.lower() not in normalized:
        problems.append("la respuesta correcta no está entre las opciones")
    if any("todas las" in option or "ninguna de" in option for option in normalized):
        problems.append("usa 'todas/ninguna de las anteriores'")

    # No se comprueba si el enunciado contiene la respuesta: parece una
    # fuga, pero en una pregunta de comprensión ("Escuchas: 'I'm a
    # teacher.' ¿Qué profesión tiene?") es justo lo que se evalúa. Esa
    # regla rechazó así una pregunta válida seis veces seguidas.
    return problems


async def verify_answer_key(questions: list[dict]) -> dict[int, str]:
    """Resuelve las preguntas SIN ver la clave y devuelve, por índice, las
    que no coinciden con ella.

    La validación de forma no puede ver el fallo más caro de un examen:
    una pregunta con dos respuestas correctas. Pasó en la primera prueba:
    "¿Cómo respondes si tienes 30 años?" daba por buena solo "I'm 30." y
    marcaba mal "I am 30 years old.", que también es correcta. Un alumno
    que responde bien suspendería, y en un examen que decide si avanza eso
    es lo peor que puede pasar.
    """
    llm = get_llm(model_id=settings.llm_model, temperature=0.0, max_tokens=2000)
    listing = "\n\n".join(
        f"{index}. {question['prompt']}\n" + "\n".join(f"   - {option}" for option in question["options"])
        for index, question in enumerate(questions, start=1)
    )
    response = await ainvoke_serialized(
        lambda: llm.ainvoke([HumanMessage(content=VERIFY_PROMPT.format(questions=listing))]),
        purpose="exam_verification",
    )

    match = re.search(r"\{.*\}", response.content, re.DOTALL)
    answers = json.loads(match.group(0), strict=False).get("answers", []) if match else []
    if len(answers) != len(questions):
        # Sin una respuesta por pregunta no se puede verificar ninguna:
        # se rechazan todas antes que aceptar una clave sin comprobar.
        return {index: "no se pudo verificar la clave" for index in range(len(questions))}

    rejected: dict[int, str] = {}
    for index, (question, verdict) in enumerate(zip(questions, answers)):
        if not isinstance(verdict, dict):
            rejected[index] = "no se pudo verificar la clave"
            continue
        accepted_norm = {str(option).strip().lower() for option in verdict.get("correct", [])}
        correct = str(question["correct"]).strip().lower()
        if verdict.get("giveaway"):
            # Pasó en la primera tanda: "¿Qué palabra tiene el sonido /iː/
            # como en 'see'?" con "see" como respuesta.
            rejected[index] = "la pregunta se acierta copiando el enunciado"
        elif correct not in accepted_norm:
            rejected[index] = f"la clave {question['correct']!r} no parece correcta"
        elif len(accepted_norm) > 1:
            # El verificador es "generoso" a propósito: basta que otra opción
            # sea defendible. Pasó con "I like doing this" como única
            # respuesta y "I like art" marcada mal: un alumno que razona bien
            # suspendería esa pregunta.
            rejected[index] = f"hay más de una respuesta defendible: {sorted(accepted_norm)}"
    return rejected


async def generate_module_exam(
    module: Module, descriptor_statements: dict[str, str], descriptor_skills: dict[str, str]
) -> list[ExamQuestion]:
    """Genera el examen pidiendo preguntas de sobra y quedándose con las
    que pasan los dos filtros.

    Antes se validaba el examen entero de una vez y cualquier pregunta
    dudosa lo tumbaba. No convergía: el modelo se empeñaba en una pregunta
    de edad con tres formas correctas ("I'm 30.", "I'm thirty.", "I am 30
    years old."), y en cada corrección reescribía el examen y rompía otra
    que ya estaba bien. Ahora cada pregunta se juzga sola: la dudosa se
    descarta y se piden solo las que faltan.
    """
    from app.agents.prompt_builder import SPANISH_VARIETY

    llm = get_llm(model_id=settings.llm_model, temperature=0.5, max_tokens=3500)
    codes = exam_descriptor_codes(module, descriptor_skills)
    per_code_cap = max_questions_per_code(len(codes))
    context = _format_context(module, descriptor_statements, codes)
    base_prompt = USER_PROMPT.format(**context, spanish_variety=SPANISH_VARIETY)

    accepted: list[dict] = []
    seen_prompts: set[str] = set()
    rejected_notes: list[str] = []

    for round_number in range(settings.exam_generation_max_attempts):
        missing = EXAM_QUESTION_COUNT - len(accepted)
        per_code = {code: sum(q["descriptor_code"] == code for q in accepted) for code in codes}
        open_codes = [code for code, used in per_code.items() if used < per_code_cap]

        request = base_prompt.replace(
            f"Exactamente {EXAM_QUESTION_COUNT} preguntas", f"Exactamente {missing + EXTRA_PER_ROUND} preguntas"
        )
        if accepted:
            request += (
                "\n\nYa tengo estas preguntas, no las repitas:\n"
                + "\n".join(f"- {q['prompt']}" for q in accepted)
                + f"\n\nUsa solo estos códigos: {', '.join(open_codes)}."
            )
        if rejected_notes:
            # Se le cuenta por qué se descartaron las anteriores para que
            # no vuelva a caer en lo mismo.
            request += "\n\nEvita estos fallos de preguntas descartadas:\n" + "\n".join(
                f"- {note}" for note in rejected_notes[-6:]
            )

        response = await ainvoke_serialized(
            lambda: llm.ainvoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=request)]),
            purpose="exam_generation",
        )
        try:
            candidates = _parse(response.content)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Ronda %d de %s: JSON inválido (%s)", round_number + 1, module.code, exc)
            continue

        shaped: list[dict] = []
        for question in candidates:
            problems = question_problems(question, codes)
            prompt_key = str(question.get("prompt", "")).strip().lower()
            if prompt_key in seen_prompts:
                problems.append("enunciado repetido")
            if problems:
                rejected_notes.append(f"{question.get('prompt', '')!r}: {'; '.join(problems)}")
                continue
            shaped.append(question)

        if not shaped:
            continue

        # La verificación cuesta una llamada: solo se hace con las que ya
        # tienen la forma correcta.
        ambiguous = await verify_answer_key(shaped)
        for index, question in enumerate(shaped):
            if index in ambiguous:
                rejected_notes.append(f"{question['prompt']!r}: {ambiguous[index]}")
                continue
            code = question["descriptor_code"]
            if sum(q["descriptor_code"] == code for q in accepted) >= per_code_cap:
                continue
            # Dos preguntas con la misma respuesta correcta miden lo mismo:
            # pasó con dos formas de rechazar una invitación cuya respuesta
            # era, palabra por palabra, "I'd love to, but I can't. Maybe
            # another day?". Una de las dos ocupa el hueco de otra capacidad.
            answer_key = str(question["correct"]).strip().lower()
            if any(str(q["correct"]).strip().lower() == answer_key for q in accepted):
                rejected_notes.append(f"{question['prompt']!r}: repite la respuesta de otra pregunta")
                continue
            accepted.append(question)
            seen_prompts.add(question["prompt"].strip().lower())
            if len(accepted) == EXAM_QUESTION_COUNT:
                return [_build_question(q) for q in accepted]

        logger.warning(
            "Ronda %d de %s: %d/%d preguntas válidas", round_number + 1, module.code, len(accepted), EXAM_QUESTION_COUNT
        )

    raise ValueError(
        f"No se lograron {EXAM_QUESTION_COUNT} preguntas válidas para {module.code} "
        f"(quedaron {len(accepted)}). Últimos descartes: {'; '.join(rejected_notes[-3:])}"
    )


def _build_question(raw: dict) -> ExamQuestion:
    options = [str(option).strip() for option in raw["options"]]
    correct_lower = str(raw["correct"]).strip().lower()
    # La respuesta guardada es el texto EXACTO de la opción, no el que
    # escribió el modelo en "correct": la corrección compara contra lo que
    # el alumno pulsa, y basta una mayúscula distinta para suspenderle.
    correct = next(option for option in options if option.lower() == correct_lower)
    # Los modelos tienden a poner la correcta la primera. Sin barajar, un
    # alumno que marca siempre "A" aprobaría.
    random.shuffle(options)
    return ExamQuestion(
        descriptor_code=str(raw["descriptor_code"]).strip(),
        prompt=str(raw["prompt"]).strip(),
        options=options,
        correct=correct,
    )
