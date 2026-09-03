"""Siembra el catálogo de los 35 descriptores MCER de A1, tal como los
define el documento DESCRIPTORS A1 (redacción propia basada en el MCER y
su Volumen Complementario 2020).

Uso:
    python -m app.scripts.seed_a1_descriptors

Idempotente por `code`: si un descriptor ya existe, se actualiza en sitio
con el contenido de aquí abajo (mismo criterio que seed_a1_modules.py).

Requiere que exista el nivel A1 (`python -m app.scripts.seed_cefr_levels`).
"""

import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel, Descriptor

A1_DESCRIPTORS = [
    # ─────────────────────── COMPRENSIÓN ORAL (listening) ───────────────────────
    {
        "code": "A1.LI.01",
        "skill": "listening",
        "statement_en": (
            "Can recognise familiar words and very basic phrases about themselves, "
            "their family and immediate surroundings when people speak slowly and clearly."
        ),
        "statement_es": (
            "Reconoce palabras y frases muy básicas sobre sí mismo, su familia y su "
            "entorno inmediato cuando se habla despacio y con claridad."
        ),
        "modules": ["A1.M01", "A1.M02", "A1.M04"],
    },
    {
        "code": "A1.LI.02",
        "skill": "listening",
        "statement_en": "Can understand simple instructions and follow short directions given slowly.",
        "statement_es": "Entiende instrucciones sencillas y sigue indicaciones breves dadas despacio.",
        "modules": ["A1.M06"],
    },
    {
        "code": "A1.LI.03",
        "skill": "listening",
        "statement_en": "Can catch numbers, prices, times and dates when clearly spoken.",
        "statement_es": "Capta números, precios, horas y fechas dichos con claridad.",
        "modules": ["A1.M01", "A1.M03", "A1.M06"],
        "note": (
            "Alta carga cognitiva para hispanohablantes: /θɜːtiːn/ vs /ˈθɜːti/ (13/30). "
            "Requiere práctica dedicada."
        ),
    },
    {
        "code": "A1.LI.04",
        "skill": "listening",
        "statement_en": "Can identify the topic of a slow, clearly articulated conversation held in their presence.",
        "statement_es": (
            "Identifica el tema de una conversación lenta y claramente articulada que "
            "ocurre en su presencia."
        ),
        "modules": ["A1.M07", "A1.M09"],
    },
    # ────────────────────── COMPRENSIÓN LECTORA (reading) ───────────────────────
    {
        "code": "A1.RE.01",
        "skill": "reading",
        "statement_en": "Can understand familiar names, words and very simple sentences on signs, notices and posters.",
        "statement_es": "Comprende nombres conocidos, palabras y frases muy simples en carteles, letreros y avisos.",
        "modules": ["A1.M04", "A1.M06"],
    },
    {
        "code": "A1.RE.02",
        "skill": "reading",
        "statement_en": (
            "Can get an idea of the content of simple informational material such as a "
            "menu, timetable or short advertisement."
        ),
        "statement_es": (
            "Se hace una idea del contenido de material informativo sencillo como un "
            "menú, un horario o un anuncio breve."
        ),
        "modules": ["A1.M05", "A1.M06"],
    },
    {
        "code": "A1.RE.03",
        "skill": "reading",
        "statement_en": "Can understand short, simple personal messages such as a postcard, text message or profile description.",
        "statement_es": (
            "Comprende mensajes personales breves y sencillos como una postal, un "
            "mensaje de texto o una descripción de perfil."
        ),
        "modules": ["A1.M02", "A1.M08"],
    },
    # ───────────────────── EXPRESIÓN ORAL (spoken_production) ───────────────────
    {
        "code": "A1.SP.01",
        "skill": "spoken_production",
        "statement_en": "Can give basic personal information: name, age, nationality, where they live and what they do.",
        "statement_es": "Da información personal básica: nombre, edad, nacionalidad, dónde vive y a qué se dedica.",
        "modules": ["A1.M01"],
        "priority": "critical",
    },
    {
        "code": "A1.SP.02",
        "skill": "spoken_production",
        "statement_en": "Can describe people they know using simple phrases about appearance, family relationship and character.",
        "statement_es": "Describe a personas conocidas con frases simples sobre apariencia, parentesco y carácter.",
        "modules": ["A1.M02"],
    },
    {
        "code": "A1.SP.03",
        "skill": "spoken_production",
        "statement_en": "Can describe their daily routine using a simple sequence of phrases.",
        "statement_es": "Describe su rutina diaria mediante una secuencia sencilla de frases.",
        "modules": ["A1.M03"],
    },
    {
        "code": "A1.SP.04",
        "skill": "spoken_production",
        "statement_en": "Can describe where they live and what is in a place using simple linked phrases.",
        "statement_es": "Describe dónde vive y qué hay en un lugar mediante frases sencillas enlazadas.",
        "modules": ["A1.M04"],
    },
    {
        "code": "A1.SP.05",
        "skill": "spoken_production",
        "statement_en": "Can say what is happening at the moment of speaking.",
        "statement_es": "Dice qué está ocurriendo en el momento de hablar.",
        "modules": ["A1.M07"],
    },
    {
        "code": "A1.SP.06",
        "skill": "spoken_production",
        "statement_en": "Can recount a past event in a short series of simple sentences.",
        "statement_es": "Relata un hecho pasado en una serie breve de oraciones simples.",
        "modules": ["A1.M08"],
    },
    {
        "code": "A1.SP.07",
        "skill": "spoken_production",
        "statement_en": "Can state simple future plans and intentions.",
        "statement_es": "Expresa planes e intenciones futuras simples.",
        "modules": ["A1.M10"],
    },
    # ──────────────────── INTERACCIÓN ORAL (spoken_interaction) ─────────────────
    {
        "code": "A1.SI.01",
        "skill": "spoken_interaction",
        "statement_en": "Can greet, introduce themselves and take leave using basic courtesy formulas.",
        "statement_es": "Saluda, se presenta y se despide usando fórmulas básicas de cortesía.",
        "modules": ["A1.M01"],
        "priority": "critical",
    },
    {
        "code": "A1.SI.02",
        "skill": "spoken_interaction",
        "statement_en": "Can ask and answer simple questions about immediate personal needs and very familiar topics.",
        "statement_es": "Formula y responde preguntas sencillas sobre necesidades inmediatas y temas muy familiares.",
        "modules": ["A1.M01", "A1.M02", "A1.M03"],
        "priority": "critical",
    },
    {
        "code": "A1.SI.03",
        "skill": "spoken_interaction",
        "statement_en": "Can indicate they are not following and ask for repetition or slower speech.",
        "statement_es": "Indica que no está siguiendo y pide repetición o que se hable más despacio.",
        "modules": ["A1.M01"],
        "priority": "critical",
        "note": (
            "Descriptor de supervivencia. Sin él, el alumno se bloquea y abandona la "
            "interacción. Debe introducirse en la primera sesión y reciclarse en todos "
            "los módulos."
        ),
    },
    {
        "code": "A1.SI.04",
        "skill": "spoken_interaction",
        "statement_en": "Can handle a simple transaction: order food, buy something, ask for a price.",
        "statement_es": "Gestiona una transacción sencilla: pedir comida, comprar algo, preguntar un precio.",
        "modules": ["A1.M05", "A1.M06"],
    },
    {
        "code": "A1.SI.05",
        "skill": "spoken_interaction",
        "statement_en": "Can ask for and give simple directions using a map or reference points.",
        "statement_es": "Pide y da indicaciones sencillas usando un mapa o puntos de referencia.",
        "modules": ["A1.M06"],
    },
    {
        "code": "A1.SI.06",
        "skill": "spoken_interaction",
        "statement_en": "Can make and respond to simple invitations, suggestions and apologies.",
        "statement_es": "Hace y responde a invitaciones, sugerencias y disculpas sencillas.",
        "modules": ["A1.M09"],
    },
    {
        "code": "A1.SI.07",
        "skill": "spoken_interaction",
        "statement_en": "Can express likes and dislikes and ask others about theirs.",
        "statement_es": "Expresa gustos y preferencias y pregunta a otros por los suyos.",
        "modules": ["A1.M05", "A1.M09"],
    },
    # ───────────────────────── EXPRESIÓN ESCRITA (writing) ──────────────────────
    {
        "code": "A1.WR.01",
        "skill": "writing",
        "statement_en": "Can fill in a form with personal details.",
        "statement_es": "Completa un formulario con datos personales.",
        "modules": ["A1.M01"],
    },
    {
        "code": "A1.WR.02",
        "skill": "writing",
        "statement_en": "Can write simple isolated phrases and sentences about themselves and familiar people.",
        "statement_es": "Escribe frases y oraciones simples y aisladas sobre sí mismo y personas conocidas.",
        "modules": ["A1.M02", "A1.M03"],
    },
    {
        "code": "A1.WR.03",
        "skill": "writing",
        "statement_en": "Can write a short, simple description of a place or a routine.",
        "statement_es": "Escribe una descripción breve y sencilla de un lugar o una rutina.",
        "modules": ["A1.M04"],
    },
    {
        "code": "A1.WR.04",
        "skill": "writing",
        "statement_en": "Can write a short account of a past event using simple connected sentences.",
        "statement_es": "Escribe un relato breve de un hecho pasado con oraciones simples conectadas.",
        "modules": ["A1.M08"],
    },
    # ────────────────── INTERACCIÓN ESCRITA (written_interaction) ───────────────
    {
        "code": "A1.WI.01",
        "skill": "written_interaction",
        "statement_en": "Can write a short, simple message: a postcard, a note, a text message.",
        "statement_es": "Escribe un mensaje breve y sencillo: una postal, una nota, un mensaje de texto.",
        "modules": ["A1.M08"],
    },
    {
        "code": "A1.WI.02",
        "skill": "written_interaction",
        "statement_en": "Can respond to a simple written invitation or request, accepting or declining.",
        "statement_es": "Responde a una invitación o petición escrita sencilla, aceptando o declinando.",
        "modules": ["A1.M09"],
    },
    # ────────────────────────────── MEDIACIÓN (mediation) ───────────────────────
    {
        "code": "A1.ME.01",
        "skill": "mediation",
        "statement_en": (
            "Can convey simple, predictable information from a Spanish text (a sign, a "
            "price, a time) to an English speaker."
        ),
        "statement_es": (
            "Transmite información sencilla y predecible de un texto en español (un "
            "cartel, un precio, una hora) a un angloparlante."
        ),
        "modules": ["A1.M06"],
        "note": (
            "Tarea natural y realista para el perfil del alumno: traducir un cartel a un "
            "turista. Genera producción rica con carga cognitiva baja."
        ),
    },
    {
        "code": "A1.ME.02",
        "skill": "mediation",
        "statement_en": "Can use a simple word, gesture or drawing to make themselves understood when vocabulary fails.",
        "statement_es": "Usa una palabra simple, un gesto o un dibujo para hacerse entender cuando le falta vocabulario.",
        "modules": ["A1.M05", "A1.M09"],
        "note": "Estrategia compensatoria. Se evalúa como éxito, no como fallo.",
    },
    # ───────────────────── COMPETENCIA FONOLÓGICA (phonology) ───────────────────
    {
        "code": "A1.PH.01",
        "skill": "phonology",
        "statement_en": "Pronunciation is intelligible to a sympathetic listener used to speakers of their language group.",
        "statement_es": (
            "Su pronunciación resulta inteligible para un oyente cooperativo "
            "acostumbrado a hablantes de su grupo lingüístico."
        ),
        "modules": ["all"],
    },
    {
        "code": "A1.PH.02",
        "skill": "phonology",
        "statement_en": "Can produce initial /s/ + consonant clusters without an added vowel.",
        "statement_es": "Produce grupos iniciales /s/ + consonante sin vocal añadida.",
        "modules": ["A1.M01", "A1.M03"],
        "l1_specific": True,
        "note": "Epéntesis: *espeak, *Espanish, *estudent. El marcador de acento más audible.",
    },
    {
        "code": "A1.PH.03",
        "skill": "phonology",
        "statement_en": "Can distinguish and produce the contrast between /ɪ/ and /iː/ in high-frequency word pairs.",
        "statement_es": "Distingue y produce el contraste entre /ɪ/ e /iː/ en pares de alta frecuencia.",
        "modules": ["A1.M02", "A1.M05"],
        "l1_specific": True,
    },
    {
        "code": "A1.PH.04",
        "skill": "phonology",
        "statement_en": "Places word stress correctly in high-frequency two- and three-syllable words.",
        "statement_es": "Acentúa correctamente palabras frecuentes de dos y tres sílabas.",
        "modules": ["A1.M04", "A1.M07"],
        "l1_specific": True,
        "priority": "critical",
        "note": (
            "Mayor retorno en inteligibilidad de todo A1. El español carece de reducción "
            "vocálica, lo que desplaza el acento y hace la palabra irreconocible."
        ),
    },
    # ──────────────────────── ALCANCE LÉXICO (lexis) ────────────────────────────
    {
        "code": "A1.LX.01",
        "skill": "lexis",
        "statement_en": "Has a basic repertoire of words and phrases relating to particular concrete situations.",
        "statement_es": "Posee un repertorio básico de palabras y frases relativas a situaciones concretas.",
        "modules": ["all"],
        "target": "~600 unidades activas al cierre de A1",
    },
    # ───────────────────── COMPETENCIA PRAGMÁTICA (pragmatics) ──────────────────
    {
        "code": "A1.PR.01",
        "skill": "pragmatics",
        "statement_en": "Can use basic mitigation when making a request instead of a bare imperative.",
        "statement_es": "Usa mitigación básica al pedir algo en lugar de un imperativo desnudo.",
        "modules": ["A1.M05", "A1.M06"],
        "l1_specific": True,
        "priority": "critical",
        "note": (
            "El español admite el imperativo directo donde el inglés exige mitigación. "
            "Sin este descriptor el alumno suena grosero sin saberlo. Se enseña desde A1, "
            "no desde B2."
        ),
    },
]


async def seed_a1_descriptors() -> None:
    async with AsyncSessionLocal() as session:
        level_result = await session.execute(select(CEFRLevel).where(CEFRLevel.code == "A1"))
        level = level_result.scalars().first()
        if level is None:
            print("No existe el nivel A1 todavía — corre antes `python -m app.scripts.seed_cefr_levels`.")
            return

        existing_result = await session.execute(select(Descriptor).where(Descriptor.level_id == level.id))
        existing_by_code = {d.code: d for d in existing_result.scalars().all()}

        inserted, updated = [], []

        for data in A1_DESCRIPTORS:
            fields = dict(
                level_id=level.id,
                code=data["code"],
                skill=data["skill"],
                statement_en=data["statement_en"],
                statement_es=data["statement_es"],
                modules=data.get("modules", []),
                priority=data.get("priority"),
                l1_specific=data.get("l1_specific", False),
                note=data.get("note"),
                target=data.get("target"),
            )

            existing = existing_by_code.get(data["code"])
            if existing is None:
                session.add(Descriptor(**fields))
                inserted.append(data["code"])
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
                updated.append(data["code"])

        await session.commit()

        if inserted:
            print(f"Insertados {len(inserted)} descriptores nuevos en A1: {', '.join(inserted)}")
        if updated:
            print(f"Sincronizados {len(updated)} descriptores ya existentes en A1.")
        print(f"Total A1: {len(A1_DESCRIPTORS)} descriptores.")


if __name__ == "__main__":
    asyncio.run(seed_a1_descriptors())
