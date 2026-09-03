"""Siembra los 10 módulos reales de A1, tal como los define el documento de
diseño curricular MCER (marco + nivel A1 desarrollado, v1.0).

Uso:
    python -m app.scripts.seed_a1_modules

Idempotente por `code` ("A1.M01".."A1.M10"): si un módulo con ese code ya
existe, se actualiza EN SITIO con el contenido de aquí abajo (así una
corrección al documento de currículo se sincroniza con un re-run, sin
duplicar filas). Si no existe, se inserta.

Antes de sembrar, retira cualquier módulo "legacy" de A1 sin `code` (los
8 módulos de ejemplo genéricos de la primera versión de este script) —
pero SOLO si nadie se inscribió todavía; si algún alumno tiene una
Enrollment contra uno de esos módulos legacy, se avisa y NO se toca (para
no destruir progreso real), y el nivel queda con módulos legacy + nuevos
mezclados hasta que se resuelva a mano.

Requiere que exista el nivel A1 (`python -m app.scripts.seed_cefr_levels`).
"""

import asyncio
from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import AsyncSessionLocal
from app.models import CEFRLevel, Enrollment, Module

# Modos MCER (10, ver DESCRIPTORS A1 § cabecera) -> bucket de 4 destrezas
# que ya consume el dashboard (Module.skill_focus, ver
# enrollment_repository.get_skill_breakdown). SI/ME/PH/PR se agrupan bajo
# "speaking" porque en ESTE currículo son abrumadoramente orales
# (interacción, mediación hablada, fonología, pragmática de habla) —
# LX se agrupa bajo "writing" por defecto al no tener naturaleza oral.
MODE_TO_SKILL_FOCUS = {
    "LI": "listening",
    "RE": "reading",
    "SP": "speaking",
    "WR": "writing",
    "SI": "speaking",
    "WI": "writing",
    "ME": "speaking",
    "PH": "speaking",
    "LX": "writing",
    "PR": "speaking",
}


def _skill_focus_from_descriptors(descriptors: list[str]) -> str:
    """Deriva el skill_focus de 4 destrezas a partir de los códigos de
    descriptor de 10 modos del módulo (ej. "A1.SI.02" -> modo "SI" ->
    bucket "speaking"). Gana el bucket con más apariciones; en empate,
    "speaking" (el modo dominante de un currículo centrado en interacción
    oral — MCER § 1.2) — así el resultado es determinista y no depende del
    orden de iteración de un dict."""
    buckets: Counter[str] = Counter()
    for code in descriptors:
        mode = code.split(".")[1] if code.count(".") >= 2 else ""
        buckets[MODE_TO_SKILL_FOCUS.get(mode, "speaking")] += 1
    if not buckets:
        return "speaking"
    top_count = max(buckets.values())
    top = {bucket for bucket, count in buckets.items() if count == top_count}
    return "speaking" if "speaking" in top else next(iter(top))


def _code(sequence: int) -> str:
    return f"A1.M{sequence:02d}"


def _recycles(*sequences: int) -> list[str]:
    return [_code(n) for n in sequences]


# ═══════════════════════════════════════════════════════════════════════
# Los 10 módulos, transcritos del documento de currículo. Los campos
# corresponden 1:1 a la "anatomía de un módulo" (§ 3 del documento) y a
# las columnas nuevas de Module (ver models/module.py).
# ═══════════════════════════════════════════════════════════════════════

A1_MODULES = [
    {
        "sequence": 1,
        "title": "Hello, I'm...",
        "title_es": "Hola, soy...",
        "estimated_hours": 10,
        "descriptors": ["A1.SI.01", "A1.SI.02", "A1.SI.03", "A1.SP.01", "A1.LI.01", "A1.LI.03", "A1.WR.01", "A1.PH.02"],
        "recycles": [],
        "communicative_objectives": [
            "Saludar y despedirse según el momento del día",
            "Presentarse y presentar a otra persona",
            "Preguntar y decir nombre, edad, nacionalidad y ocupación",
            "Deletrear el propio nombre y pedir que deletreen",
            "Pedir repetición cuando no se entiende",
        ],
        "grammar": {
            "focus": [
                "verb be: afirmativo, negativo, interrogativo (todas las personas)",
                "Pronombres personales sujeto",
                "Wh- questions básicas: what, where, how old",
                "Artículo indefinido a/an ante profesión",
            ],
            "note": (
                "be se presenta como herramienta para presentarse, no como paradigma a "
                "conjugar. Nunca se pide recitar la conjugación."
            ),
        },
        "lexis": {
            "target_items": 60,
            "sets": [
                "Saludos y despedidas",
                "Alfabeto",
                "Números 0–20",
                "Países y nacionalidades (12 de alta frecuencia para el alumno)",
                "Ocupaciones comunes (15)",
            ],
            "chunks": [
                "Nice to meet you.",
                "How do you spell that?",
                "Sorry, can you repeat that?",
                "Can you speak more slowly, please?",
                "I don't understand.",
                "What does ___ mean?",
                "My name's ___ and I'm from ___.",
            ],
        },
        "pronunciation": {
            "focus": "Grupos iniciales /s/ + consonante. Contraste /θɜːˈtiːn/ vs /ˈθɜːti/.",
            "l1_alerts": [
                "Epéntesis: *espeak, *Espanish, *estudent, *estart",
                "13 vs 30, 14 vs 40 — el acento distingue, no el sonido",
                "/h/ en hello, how — no debe ser jota ni muda",
            ],
        },
        "l1_interference": [
            {"error": "*I have 25 years", "target": "I'm 25.", "origin": "tengo 25 años", "severity": "high"},
            {
                "error": "*I'm doctor",
                "target": "I'm a doctor.",
                "origin": "Omisión de artículo ante profesión",
                "severity": "medium",
            },
            {
                "error": "*I'm from the Colombia",
                "target": "I'm from Colombia.",
                "origin": "Sobreuso del artículo con países",
                "severity": "low",
            },
            {
                "error": "*How is your name?",
                "target": "What's your name?",
                "origin": "¿Cómo te llamas?",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-01-t1",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.01",
                "prompt": "Conocer a alguien nuevo en el primer día de un curso. Saludar, presentarse, preguntar tres datos.",
                "success_criteria": "Intercambia nombre, procedencia y ocupación sin bloqueo mayor a 5 segundos.",
            },
            {
                "id": "a1-01-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.03",
                "prompt": "El tutor habla deliberadamente rápido o usa una palabra desconocida. El alumno debe pedir aclaración.",
                "success_criteria": "Usa una fórmula de reparación sin recurrir al español.",
                "note": "Tarea de supervivencia. Se evalúa el uso de la estrategia, no la comprensión final.",
            },
            {
                "id": "a1-01-t3",
                "type": "written_production",
                "descriptor": "A1.WR.01",
                "prompt": "Completar un formulario de inscripción con datos personales.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SI.01", "A1.SP.01", "A1.SI.03"]},
        "tutor_config": {
            "persona": "Cálido, muy paciente, entusiasta. Celebra cualquier intento de producción.",
            "speech_rate": "very_slow",
            "correction_policy": "Solo errores que rompen comunicación. Todo lo demás por recast implícito.",
            "scaffolds": [
                "Ofrecer el chunk completo si el alumno se bloquea más de 8 segundos",
                "Repetir la pregunta con entonación más marcada antes de reformular",
            ],
            "forbidden": [
                "Explicar la conjugación de be",
                "Corregir pronunciación en el primer intento de una palabra nueva",
                "Usar contracciones no vistas o lenguaje idiomático",
            ],
        },
    },
    {
        "sequence": 2,
        "title": "My people",
        "title_es": "Mi gente",
        "estimated_hours": 9,
        "descriptors": ["A1.SP.02", "A1.SI.02", "A1.LI.01", "A1.RE.03", "A1.WR.02", "A1.PH.03"],
        "recycles": _recycles(1),
        "communicative_objectives": [
            "Hablar de la propia familia y sus relaciones",
            "Describir el aspecto físico de una persona",
            "Describir el carácter de una persona con adjetivos básicos",
            "Decir qué se posee",
        ],
        "grammar": {
            "focus": [
                "have got / has got (posesión y descripción)",
                "Adjetivos posesivos: my, your, his, her, our, their",
                "Genitivo sajón: 's",
                "Plurales regulares e irregulares de alta frecuencia",
                "Orden adjetivo + sustantivo",
            ]
        },
        "lexis": {
            "target_items": 70,
            "sets": [
                "Miembros de la familia (18)",
                "Aspecto físico: pelo, ojos, altura, complexión",
                "Adjetivos de carácter (12)",
                "Objetos personales (15)",
            ],
            "chunks": [
                "This is my ___.",
                "She's got ___ hair.",
                "He looks like ___.",
                "We're very close.",
                "How many brothers and sisters have you got?",
            ],
        },
        "pronunciation": {
            "focus": "Contraste /ɪ/–/iː/: sister/see, his/he's, live/leave. Plural -s: /s/ /z/ /ɪz/.",
            "l1_alerts": ["Fusión /b/–/v/ en brother, very", "*sisterss con -s ensordecida"],
        },
        "l1_interference": [
            {
                "error": "*my brother is more old than me",
                "target": "My brother is older than me.",
                "origin": "más viejo",
                "severity": "medium",
                "note": "El comparativo se ve en A2. Aquí solo se hace recast, no se enseña.",
            },
            {
                "error": "*a girl blonde",
                "target": "a blonde girl",
                "origin": "Orden N+Adj del español",
                "severity": "high",
            },
            {
                "error": "*my parents live in Madrid (queriendo decir parientes)",
                "target": "my relatives",
                "origin": "Falso amigo parents/parientes",
                "severity": "medium",
            },
            {
                "error": "*the people is nice",
                "target": "The people are nice.",
                "origin": "gente = singular en español",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-02-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.02",
                "prompt": "Describir a tres miembros de la familia: quiénes son, cómo son físicamente, cómo son de carácter.",
                "success_criteria": "Produce al menos 6 frases con have got o be sin ayuda.",
            },
            {
                "id": "a1-02-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": "Juego de identificación: el tutor describe a una persona de una imagen; el alumno pregunta para adivinar cuál es.",
            },
            {
                "id": "a1-02-t3",
                "type": "written_production",
                "descriptor": "A1.WR.02",
                "prompt": "Escribir un párrafo de 5 frases presentando a la persona más importante de su vida.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SP.02"]},
        "tutor_config": {
            "persona": "Curioso, hace preguntas de seguimiento sobre la familia del alumno.",
            "correction_policy": "Corregir orden adjetivo-sustantivo siempre: es sistemático y de alto impacto. Ignorar comparativos.",
            "scaffolds": ["Ofrecer el adjetivo en español si el alumno lo pide"],
            "forbidden": [
                "Introducir comparativos o superlativos",
                "Preguntar por temas familiares sensibles (divorcio, fallecimientos) sin que el alumno los abra",
            ],
        },
    },
    {
        "sequence": 3,
        "title": "Every day",
        "title_es": "Cada día",
        "estimated_hours": 10,
        "descriptors": ["A1.SP.03", "A1.SI.02", "A1.LI.03", "A1.WR.02", "A1.PH.02"],
        "recycles": _recycles(1, 2),
        "communicative_objectives": [
            "Describir la rutina diaria propia",
            "Decir y preguntar la hora",
            "Expresar con qué frecuencia se hacen las cosas",
            "Preguntar a otros por su rutina",
        ],
        "grammar": {
            "focus": [
                "Present simple: afirmativo, negativo, interrogativo",
                "Tercera persona -s (con foco explícito)",
                "do/does como auxiliar",
                "Adverbios de frecuencia y su posición",
                "Preposiciones de tiempo: at, on, in",
            ]
        },
        "lexis": {
            "target_items": 70,
            "sets": [
                "Verbos de rutina diaria (20)",
                "Días de la semana",
                "Horas y partes del día",
                "Adverbios de frecuencia (6)",
            ],
            "chunks": [
                "I usually get up at ___.",
                "What time do you ___?",
                "On weekdays I ___, but on weekends I ___.",
                "It depends on the day.",
            ],
        },
        "pronunciation": {
            "focus": "Terminación -s en tercera persona: /s/ /z/ /ɪz/. Reducción de do you → /dʒə/.",
            "l1_alerts": ["*estudy, *estart — epéntesis persistente", "Omisión audible de -s en works, gets, watches"],
        },
        "l1_interference": [
            {
                "error": "*He work in a bank",
                "target": "He works in a bank.",
                "origin": "Ausencia de marca de 3ª persona",
                "severity": "high",
                "note": "Error más persistente de todo A1. Requiere recast en cada aparición.",
            },
            {
                "error": "*Where you live?",
                "target": "Where do you live?",
                "origin": "Sin do-support en español",
                "severity": "high",
            },
            {
                "error": "*I no like coffee",
                "target": "I don't like coffee.",
                "origin": "Negación española preverbal",
                "severity": "high",
            },
            {
                "error": "*Always I get up at seven",
                "target": "I always get up at seven.",
                "origin": "Posición libre del adverbio en español",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-03-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.03",
                "prompt": "Contar la rutina de un día típico de principio a fin, con horas.",
                "success_criteria": "Secuencia de al menos 8 acciones con marcadores temporales.",
            },
            {
                "id": "a1-03-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": "Entrevistar al tutor sobre su rutina y encontrar tres diferencias con la propia.",
                "success_criteria": "Formula al menos 5 preguntas con do/does correctamente.",
            },
            {
                "id": "a1-03-t3",
                "type": "written_production",
                "descriptor": "A1.WR.02",
                "prompt": "Escribir la rutina de un familiar, forzando el uso de tercera persona.",
                "note": "Tarea diseñada específicamente para atacar la omisión de -s.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SP.03", "A1.SI.02"]},
        "tutor_config": {
            "persona": "Estructurado. Marca las transiciones temporales con claridad.",
            "correction_policy": "Tercera persona -s y do-support se corrigen siempre. Son el núcleo del módulo.",
            "scaffolds": ["Recast enfático: repetir la frase correcta con leve énfasis en la -s"],
            "forbidden": [
                "Introducir present continuous (es del módulo 7)",
                "Corregir preposiciones de tiempo más de una vez por sesión",
            ],
        },
    },
    {
        "sequence": 4,
        "title": "Where I live",
        "title_es": "Donde vivo",
        "estimated_hours": 9,
        "descriptors": ["A1.SP.04", "A1.RE.01", "A1.WR.03", "A1.LI.01", "A1.PH.04"],
        "recycles": _recycles(2, 3),
        "communicative_objectives": [
            "Describir la propia casa y sus habitaciones",
            "Decir qué hay y qué no hay en un lugar",
            "Ubicar objetos en el espacio",
            "Describir el barrio o ciudad",
        ],
        "grammar": {
            "focus": [
                "there is / there are, afirmativo, negativo, interrogativo",
                "Preposiciones de lugar: in, on, under, next to, between, in front of, behind",
                "Artículos a/an vs the (primera aparición vs referencia conocida)",
                "some / any en contexto de cantidad indefinida",
            ]
        },
        "lexis": {
            "target_items": 65,
            "sets": [
                "Habitaciones y partes de la casa (12)",
                "Muebles y objetos domésticos (20)",
                "Lugares de la ciudad (18)",
                "Adjetivos para describir lugares (10)",
            ],
            "chunks": [
                "There's a ___ next to the ___.",
                "Is there a ___ near here?",
                "It's on the second floor.",
                "I live in a small flat in the centre.",
            ],
        },
        "pronunciation": {
            "focus": "Acento léxico en palabras de 2-3 sílabas: KITchen, BEDroom, aPARTment, resTAUrant.",
            "l1_alerts": [
                "Sin reducción vocálica → todas las sílabas plenas → acento desplazado",
                "*resTAUranT con -t final marcada",
            ],
        },
        "l1_interference": [
            {
                "error": "*In my city have many parks",
                "target": "In my city there are many parks.",
                "origin": "hay = forma de haber",
                "severity": "high",
                "note": "Error emblemático. Alta frecuencia, no rompe comunicación pero es muy marcado.",
            },
            {
                "error": "*It has a table in the kitchen",
                "target": "There's a table in the kitchen.",
                "origin": "Mismo origen",
                "severity": "high",
            },
            {
                "error": "*I live in a house very big",
                "target": "I live in a very big house.",
                "origin": "Orden N+Adj",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-04-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.04",
                "prompt": "Hacer un recorrido guiado por la propia casa habitación por habitación.",
                "success_criteria": "Usa there is/are al menos 8 veces y 4 preposiciones distintas.",
            },
            {
                "id": "a1-04-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": "El tutor describe una habitación; el alumno la dibuja o la reconstruye verbalmente y verifica.",
            },
            {
                "id": "a1-04-t3",
                "type": "written_production",
                "descriptor": "A1.WR.03",
                "prompt": "Escribir un anuncio de alquiler del propio piso para un portal inmobiliario.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SP.04"]},
        "tutor_config": {
            "persona": "Visual. Pide detalles espaciales concretos.",
            "correction_policy": "have → there is/are se corrige siempre. Es el objetivo central.",
            "forbidden": ["Usar vocabulario arquitectónico fuera de las listas del módulo"],
        },
    },
    {
        "sequence": 5,
        "title": "Food and drink",
        "title_es": "Comida y bebida",
        "estimated_hours": 10,
        "descriptors": ["A1.SI.04", "A1.SI.07", "A1.RE.02", "A1.ME.02", "A1.PH.03", "A1.PR.01"],
        "recycles": _recycles(3, 4),
        "communicative_objectives": [
            "Pedir comida y bebida en un restaurante o cafetería",
            "Expresar gustos y aversiones alimentarias",
            "Preguntar por ingredientes y precios",
            "Formular peticiones con cortesía adecuada",
        ],
        "grammar": {
            "focus": [
                "like / love / hate + sustantivo",
                "Sustantivos contables e incontables",
                "some / any en peticiones y preguntas",
                "would like como fórmula de petición",
                "How much / How many",
            ]
        },
        "lexis": {
            "target_items": 75,
            "sets": [
                "Alimentos básicos (30)",
                "Bebidas (12)",
                "Recipientes y cantidades: a bottle of, a slice of, a cup of",
                "Adjetivos de sabor (8)",
            ],
            "chunks": [
                "I'd like a ___, please.",
                "Could I have the bill, please?",
                "Does it have ___ in it?",
                "I'm allergic to ___.",
                "I'm not a big fan of ___.",
                "Anything to drink?",
            ],
        },
        "pronunciation": {
            "focus": "Contraste /ɪ/–/iː/: chicken/cheek, fish/feet. Reducción en would you /wʊdʒə/.",
            "l1_alerts": ["*chiken con /iː/", "*esoup, *espaghetti"],
        },
        "l1_interference": [
            {
                "error": "*Give me a coffee",
                "target": "Could I have a coffee, please?",
                "origin": "El imperativo directo es neutro en español",
                "severity": "critical",
                "note": (
                    "Error pragmático, no gramatical. La frase es correcta y suena grosera. "
                    "Es el error de mayor coste social de todo A1 y el que ningún currículo "
                    "genérico trata."
                ),
            },
            {
                "error": "*I want a water",
                "target": "I'd like some water.",
                "origin": "quiero + incontable como contable",
                "severity": "high",
            },
            {
                "error": "*I like very much the pizza",
                "target": "I really like pizza.",
                "origin": "Orden + artículo con sustantivo genérico",
                "severity": "medium",
            },
            {
                "error": "*I am constipated (queriendo decir resfriado)",
                "target": "I have a cold.",
                "origin": "Falso amigo constipado",
                "severity": "high",
                "note": "Tratar explícitamente. Produce situaciones socialmente graves.",
            },
        ],
        "tasks": [
            {
                "id": "a1-05-t1",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.04",
                "prompt": "Pedir una comida completa en un restaurante, preguntar por un ingrediente y pedir la cuenta.",
                "success_criteria": "Completa la transacción usando mitigación en todas las peticiones.",
            },
            {
                "id": "a1-05-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.PR.01",
                "prompt": "El tutor presenta cuatro peticiones, dos corteses y dos bruscas. El alumno identifica cuáles suenan mal y las reformula.",
                "note": "Tarea de conciencia pragmática. Central en este módulo.",
            },
            {
                "id": "a1-05-t3",
                "type": "mediation",
                "descriptor": "A1.ME.02",
                "prompt": "Describir un plato típico del país del alumno sin conocer su nombre en inglés, usando circunloquio.",
                "success_criteria": "Consigue que el tutor identifique el plato usando solo léxico A1.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SI.04", "A1.PR.01"]},
        "tutor_config": {
            "persona": "Camarero amable en juego de rol; profesor reflexivo fuera de él.",
            "correction_policy": (
                "La mitigación se corrige siempre y se explica el porqué en español. El "
                "alumno debe entender que no es un error gramatical sino de registro."
            ),
            "scaffolds": ["Ofrecer el chunk de petición completo tras un imperativo desnudo"],
            "forbidden": [
                "Ridiculizar el error pragmático — se explica con neutralidad cultural",
                "Introducir would como condicional",
            ],
        },
    },
    {
        "sequence": 6,
        "title": "Getting around",
        "title_es": "Moverse por la ciudad",
        "estimated_hours": 10,
        "descriptors": ["A1.SI.05", "A1.SI.04", "A1.LI.02", "A1.RE.01", "A1.RE.02", "A1.ME.01", "A1.PR.01"],
        "recycles": _recycles(4, 5),
        "communicative_objectives": [
            "Pedir y dar indicaciones para llegar a un lugar",
            "Comprar un billete de transporte",
            "Preguntar precios y horarios",
            "Traducir un cartel en español para un angloparlante",
        ],
        "grammar": {
            "focus": [
                "Imperativos para indicaciones: go, turn, take, cross",
                "can para posibilidad y petición",
                "Preposiciones de movimiento y dirección",
                "How far / How long",
            ]
        },
        "lexis": {
            "target_items": 65,
            "sets": [
                "Transporte público (12)",
                "Verbos de dirección (10)",
                "Puntos de referencia urbanos (15)",
                "Números 20–1000 y precios",
            ],
            "chunks": [
                "Excuse me, how do I get to ___?",
                "Go straight on and turn left at the ___.",
                "It's about ten minutes on foot.",
                "A return ticket to ___, please.",
                "Does this bus go to ___?",
            ],
        },
        "pronunciation": {
            "focus": "Entonación ascendente en preguntas de cortesía. Acento en números: fifTEEN vs FIFty.",
            "l1_alerts": ["Entonación plana en Excuse me → suena a demanda", "*estation, *estreet"],
        },
        "l1_interference": [
            {
                "error": "*Where is the station? (sin Excuse me)",
                "target": "Excuse me, where's the station?",
                "origin": "Menor necesidad de apertura ritual en español",
                "severity": "high",
            },
            {
                "error": "*I take the bus in the corner",
                "target": "on the corner",
                "origin": "Calco preposicional",
                "severity": "low",
            },
            {"error": "*Is far?", "target": "Is it far?", "origin": "Sujeto nulo", "severity": "high"},
            {
                "error": "*How much time?",
                "target": "How long?",
                "origin": "cuánto tiempo",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-06-t1",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.05",
                "prompt": "Un turista pregunta cómo llegar del punto A al punto B en el mapa del barrio del alumno. Dar la ruta completa.",
                "success_criteria": "Ruta comprensible con al menos 4 instrucciones secuenciadas.",
            },
            {
                "id": "a1-06-t2",
                "type": "mediation",
                "descriptor": "A1.ME.01",
                "prompt": "Hay un cartel en español (horario de un museo, aviso de cierre). Explicárselo a un visitante que no lo entiende.",
                "success_criteria": "Transmite la información esencial sin traducir palabra por palabra.",
                "note": "Tarea de mediación característica del perfil del alumno.",
            },
            {
                "id": "a1-06-t3",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.04",
                "prompt": "Comprar un billete: destino, tipo, precio, andén.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SI.05", "A1.ME.01"]},
        "tutor_config": {
            "persona": "Turista perdido en juego de rol. Comete errores deliberados para forzar reparación.",
            "correction_policy": "Sujeto nulo (*Is far?) se corrige siempre. Preposiciones se dejan pasar.",
            "scaffolds": ["Repetir la última instrucción entendida y pedir la siguiente"],
        },
    },
    {
        "sequence": 7,
        "title": "Right now",
        "title_es": "Ahora mismo",
        "estimated_hours": 9,
        "descriptors": ["A1.SP.05", "A1.LI.04", "A1.SI.02", "A1.PH.04"],
        "recycles": _recycles(3, 4),
        "communicative_objectives": [
            "Describir lo que ocurre en el momento de hablar",
            "Describir el tiempo atmosférico",
            "Hablar de ropa y de lo que alguien lleva puesto",
            "Contrastar rutina y momento actual",
        ],
        "grammar": {
            "focus": [
                "Present continuous: afirmativo, negativo, interrogativo",
                "Contraste present simple vs present continuous",
                "Reglas de -ing",
            ]
        },
        "lexis": {
            "target_items": 60,
            "sets": ["Ropa y accesorios (22)", "Tiempo atmosférico (12)", "Verbos de acción observable (15)", "Colores (11)"],
            "chunks": [
                "What are you doing?",
                "I'm just ___ing.",
                "It's raining / It's sunny.",
                "She's wearing a ___.",
                "Right now I'm ___, but I usually ___.",
            ],
        },
        "pronunciation": {
            "focus": "Terminación -ing sin /g/ audible. Acento en el verbo léxico, no en el auxiliar.",
            "l1_alerts": ["*workinG con /g/ final marcada", "*Is raining sin sujeto"],
        },
        "l1_interference": [
            {
                "error": "*Is raining",
                "target": "It's raining.",
                "origin": "Sujeto nulo — verbos meteorológicos en español no llevan sujeto",
                "severity": "critical",
                "note": "El caso más resistente de sujeto nulo. Requiere tratamiento explícito.",
            },
            {
                "error": "*I go to the store now",
                "target": "I'm going to the store now.",
                "origin": "El presente español cubre el continuo",
                "severity": "high",
            },
            {"error": "*I am agree", "target": "I agree.", "origin": "estoy de acuerdo", "severity": "medium"},
            {
                "error": "*She's wearing a shirt blue",
                "target": "a blue shirt",
                "origin": "Orden N+Adj — reciclado del módulo 2",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-07-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.05",
                "prompt": "Describir en directo lo que ocurre en una escena concurrida (imagen o descripción del tutor).",
                "success_criteria": "Al menos 8 frases en present continuous con sujetos variados.",
            },
            {
                "id": "a1-07-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": "Contrastar: qué hace normalmente los sábados vs qué está haciendo ahora.",
                "success_criteria": "Alterna correctamente los dos tiempos al menos 4 veces.",
                "note": "Tarea diseñada para el contraste, no para practicar un tiempo aislado.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SP.05"]},
        "tutor_config": {
            "persona": "Observador, describe escenas con detalle.",
            "correction_policy": "Sujeto nulo se corrige siempre. Es el objetivo estructural del módulo.",
            "forbidden": ["Introducir present continuous con valor de futuro"],
        },
    },
    {
        "sequence": 8,
        "title": "Last weekend",
        "title_es": "El fin de semana pasado",
        "estimated_hours": 11,
        "descriptors": ["A1.SP.06", "A1.WR.04", "A1.WI.01", "A1.RE.03", "A1.LI.01"],
        "recycles": _recycles(3, 5, 7),
        "communicative_objectives": [
            "Contar qué se hizo en un momento pasado concreto",
            "Preguntar a otros sobre su pasado reciente",
            "Escribir un mensaje contando algo que ocurrió",
        ],
        "grammar": {
            "focus": [
                "Past simple de be: was / were",
                "Past simple regular: -ed",
                "Past simple irregular: 20 verbos de altísima frecuencia",
                "did / didn't como auxiliar",
                "Marcadores temporales de pasado: yesterday, last, ago",
            ]
        },
        "lexis": {
            "target_items": 70,
            "sets": [
                "Verbos irregulares nucleares (20): go, have, do, see, eat, buy, get, come, make, "
                "take, meet, say, tell, give, find, know, think, feel, leave, put",
                "Expresiones de tiempo pasado (12)",
                "Actividades de ocio (15)",
            ],
            "chunks": [
                "Last weekend I went to ___.",
                "It was great / It was awful.",
                "What did you do yesterday?",
                "I didn't do much, actually.",
            ],
        },
        "pronunciation": {
            "focus": "Terminación -ed: /t/ en worked, /d/ en played, /ɪd/ en wanted.",
            "l1_alerts": [
                "*workED como sílaba plena en todos los casos",
                "Reducción de grupos finales: *aks por asked, *lookt bien pero *walk-ed mal",
            ],
        },
        "l1_interference": [
            {
                "error": "*I go to the beach yesterday",
                "target": "I went to the beach yesterday.",
                "origin": "Ausencia de marca de pasado por transferencia parcial",
                "severity": "high",
            },
            {
                "error": "*I didn't went",
                "target": "I didn't go.",
                "origin": "Doble marca de pasado",
                "severity": "high",
                "note": "Error de sobregeneralización, señal de que la regla se está internalizando. Buena señal pedagógica.",
            },
            {
                "error": "*Did you went?",
                "target": "Did you go?",
                "origin": "Misma sobregeneralización",
                "severity": "high",
            },
            {
                "error": "*I was in the party",
                "target": "I was at the party.",
                "origin": "Calco preposicional",
                "severity": "low",
            },
        ],
        "tasks": [
            {
                "id": "a1-08-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.06",
                "prompt": "Contar el último fin de semana con al menos seis acciones en orden cronológico.",
                "success_criteria": "Secuencia coherente, mayoría de verbos en pasado correcto.",
            },
            {
                "id": "a1-08-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": "Entrevistar al tutor sobre unas vacaciones. Cinco preguntas con did.",
            },
            {
                "id": "a1-08-t3",
                "type": "written_interaction",
                "descriptor": "A1.WI.01",
                "prompt": "Escribir un mensaje a un amigo contando algo que pasó ayer.",
            },
        ],
        "assessment": {
            "evidence_required": 4,
            "gate_descriptors": ["A1.SP.06", "A1.WR.04"],
            "note": "Se exige más evidencia: el pasado simple es el contenido de mayor carga del nivel.",
        },
        "tutor_config": {
            "persona": "Narrativo. Cuenta sus propias anécdotas breves como modelo.",
            "correction_policy": (
                "Doble marca de pasado (*didn't went) se corrige siempre. Verbos irregulares "
                "fuera de la lista nuclear se ofrecen sin penalizar."
            ),
            "scaffolds": ["Dar la forma irregular si el alumno la busca más de 5 segundos"],
            "forbidden": [
                "Introducir present perfect bajo ninguna circunstancia",
                "Exigir verbos irregulares fuera de los 20 nucleares",
            ],
        },
    },
    {
        "sequence": 9,
        "title": "Free time",
        "title_es": "Tiempo libre",
        "estimated_hours": 9,
        "descriptors": ["A1.SI.06", "A1.SI.07", "A1.WI.02", "A1.LI.04", "A1.ME.02", "A1.PR.01"],
        "recycles": _recycles(5, 8),
        "communicative_objectives": [
            "Hablar de aficiones y habilidades",
            "Invitar a alguien a hacer algo",
            "Aceptar y rechazar invitaciones con cortesía",
            "Proponer alternativas",
        ],
        "grammar": {
            "focus": [
                "like / love / enjoy + verbo -ing",
                "can / can't para habilidad",
                "Would you like to...? como invitación",
                "Let's... y How about...? para sugerencias",
            ]
        },
        "lexis": {
            "target_items": 65,
            "sets": [
                "Aficiones y deportes (25)",
                "Instrumentos y actividades creativas (10)",
                "Fórmulas de invitación y respuesta (12)",
            ],
            "chunks": [
                "Would you like to ___?",
                "That sounds great!",
                "I'd love to, but I can't.",
                "How about Saturday instead?",
                "I'm not very good at ___.",
                "Sorry, I'm busy that day.",
            ],
        },
        "pronunciation": {
            "focus": "can /kən/ átono vs can't /kɑːnt/ tónico. Entonación de invitación.",
            "l1_alerts": ["can pronunciado siempre pleno → confusión con can't", "Entonación descendente en invitación → suena a orden"],
        },
        "l1_interference": [
            {
                "error": "*I like play football",
                "target": "I like playing football.",
                "origin": "me gusta jugar — infinitivo en español",
                "severity": "high",
            },
            {
                "error": "*No, I can't. (sin más)",
                "target": "I'd love to, but I can't. Maybe another day?",
                "origin": "El rechazo escueto es aceptable en español",
                "severity": "high",
                "note": "Error pragmático. El inglés exige mitigar el rechazo con excusa y alternativa.",
            },
            {
                "error": "*I'm good in tennis",
                "target": "I'm good at tennis.",
                "origin": "Calco preposicional",
                "severity": "low",
            },
            {
                "error": "*I practise sport",
                "target": "I do sport / I play sports.",
                "origin": "hacer deporte",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-09-t1",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.06",
                "prompt": "Organizar un plan con el tutor: proponer, negociar día y hora, cerrar el acuerdo.",
                "success_criteria": "Completa la negociación con al menos una contrapropuesta.",
            },
            {
                "id": "a1-09-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.06",
                "prompt": "Rechazar tres invitaciones sucesivas sin sonar descortés.",
                "note": "Tarea pragmática. Se evalúa el grado de mitigación, no la gramática.",
            },
            {
                "id": "a1-09-t3",
                "type": "written_interaction",
                "descriptor": "A1.WI.02",
                "prompt": "Responder por escrito a una invitación aceptando, y a otra declinando.",
            },
        ],
        "assessment": {"evidence_required": 3, "gate_descriptors": ["A1.SI.06", "A1.SI.07"]},
        "tutor_config": {
            "persona": "Sociable, propone planes, insiste amablemente para forzar el rechazo cortés.",
            "correction_policy": "like + -ing se corrige siempre. El rechazo escueto se trabaja explícitamente.",
            "forbidden": ["Aceptar un rechazo escueto sin trabajarlo"],
        },
    },
    {
        "sequence": 10,
        "title": "What's next",
        "title_es": "Lo que viene",
        "estimated_hours": 8,
        "descriptors": ["A1.SP.07", "A1.SI.02", "A1.WR.02", "A1.LX.01", "A1.PH.01"],
        "recycles": _recycles(1, 3, 5, 7, 8, 9),
        "communicative_objectives": [
            "Hablar de planes e intenciones futuras",
            "Preguntar a otros por sus planes",
            "Consolidar e integrar todo el nivel",
        ],
        "grammar": {
            "focus": [
                "be going to para intención y plan",
                "Marcadores de futuro: tomorrow, next, in + tiempo",
                "Repaso integrado de los tres tiempos del nivel",
            ]
        },
        "lexis": {
            "target_items": 50,
            "sets": ["Expresiones de futuro (10)", "Metas y propósitos (12)", "Consolidación de campos anteriores"],
            "chunks": [
                "I'm going to ___ next month.",
                "What are your plans for ___?",
                "I'm not sure yet.",
                "Hopefully I'll ___.",
            ],
        },
        "pronunciation": {
            "focus": "going to → /ˈɡənə/ en habla natural. Comprensión, no producción obligatoria.",
            "l1_alerts": ["Incomprensión de gonna en input auténtico"],
        },
        "l1_interference": [
            {
                "error": "*Tomorrow I go to Madrid",
                "target": "Tomorrow I'm going to Madrid.",
                "origin": "El presente español expresa futuro",
                "severity": "high",
            },
            {
                "error": "*I am going to the gym every day (queriendo expresar rutina)",
                "target": "I go to the gym every day.",
                "origin": "Confusión de aspecto en el repaso",
                "severity": "medium",
            },
        ],
        "tasks": [
            {
                "id": "a1-10-t1",
                "type": "spoken_production",
                "descriptor": "A1.SP.07",
                "prompt": "Contar tres planes concretos para los próximos meses y por qué.",
            },
            {
                "id": "a1-10-t2",
                "type": "spoken_interaction",
                "descriptor": "A1.SI.02",
                "prompt": (
                    "Conversación integradora de 10 minutos que atraviesa rutina, un recuerdo "
                    "pasado, lo que ocurre ahora y planes futuros."
                ),
                "success_criteria": (
                    "Sostiene la conversación alternando los tres tiempos con precisión "
                    "mayoritaria y sin bloqueos superiores a 8 segundos."
                ),
                "note": "Tarea de salida del nivel. Evidencia principal para la transición a A2.",
            },
            {
                "id": "a1-10-t3",
                "type": "written_production",
                "descriptor": "A1.WR.02",
                "prompt": "Escribir un texto de 100 palabras: quién soy, qué hago, qué hice el año pasado, qué voy a hacer.",
            },
        ],
        "assessment": {
            "evidence_required": 4,
            "gate_descriptors": ["A1.SP.07"],
            "level_exit_criteria": [
                "Todos los descriptores marcados priority: critical con mastery >= 0.8",
                "Al menos 80% del total de descriptores A1 con mastery >= 0.7",
                "Tarea a1-10-t2 superada en dos ocasiones distintas",
            ],
        },
        "tutor_config": {
            "persona": "Reflexivo. Ayuda al alumno a ver cuánto ha avanzado desde el módulo 1.",
            "correction_policy": "Repaso integral. Se corrigen errores de cualquier módulo del nivel.",
            "scaffolds": ["Recordar al alumno la primera sesión como referencia de progreso"],
            "forbidden": [
                "Introducir will (corresponde a A2)",
                "Cerrar el nivel sin verificar los level_exit_criteria",
            ],
        },
    },
]


async def _retire_legacy_modules(session, level_id) -> list[str]:
    """Borra los módulos de A1 sin `code` (versión de ejemplo anterior de
    este script) que NO tengan ninguna Enrollment — devuelve los títulos
    que no se pudieron retirar (con inscripciones, o con lecciones que
    disparan el RESTRICT de la FK) para que el operador los revise a mano."""
    result = await session.execute(select(Module).where(Module.level_id == level_id, Module.code.is_(None)))
    legacy_modules = list(result.scalars().all())
    if not legacy_modules:
        return []

    blocked = []
    for module in legacy_modules:
        has_enrollment = (
            await session.execute(select(Enrollment.id).where(Enrollment.module_id == module.id).limit(1))
        ).first()
        if has_enrollment is not None:
            blocked.append(module.title)
            continue
        try:
            await session.delete(module)
            await session.flush()
        except IntegrityError:
            await session.rollback()
            blocked.append(module.title)

    return blocked


async def seed_a1_modules() -> None:
    async with AsyncSessionLocal() as session:
        level_result = await session.execute(select(CEFRLevel).where(CEFRLevel.code == "A1"))
        level = level_result.scalars().first()
        if level is None:
            print("No existe el nivel A1 todavía — corre antes `python -m app.scripts.seed_cefr_levels`.")
            return

        blocked_titles = await _retire_legacy_modules(session, level.id)
        if blocked_titles:
            print(
                "Aviso: no se pudieron retirar estos módulos legacy de A1 (tienen inscripciones "
                f"o lecciones): {', '.join(blocked_titles)}. Revísalos a mano antes de confiar en "
                "el bloqueo secuencial por 'order'."
            )

        existing_result = await session.execute(
            select(Module).where(Module.level_id == level.id, Module.code.isnot(None))
        )
        existing_by_code = {m.code: m for m in existing_result.scalars().all()}

        inserted, updated = [], []

        for data in A1_MODULES:
            code = _code(data["sequence"])
            skill_focus = _skill_focus_from_descriptors(data["descriptors"])

            fields = dict(
                level_id=level.id,
                code=code,
                title=data["title"],
                title_es=data["title_es"],
                skill_focus=skill_focus,
                order=data["sequence"],
                estimated_hours=data["estimated_hours"],
                descriptors=data["descriptors"],
                recycles=data["recycles"],
                communicative_objectives=data["communicative_objectives"],
                grammar=data["grammar"],
                lexis=data["lexis"],
                pronunciation=data["pronunciation"],
                l1_interference=data["l1_interference"],
                tasks=data["tasks"],
                assessment=data["assessment"],
                tutor_config=data["tutor_config"],
            )

            existing = existing_by_code.get(code)
            if existing is None:
                session.add(Module(**fields))
                inserted.append(f"{data['sequence']}. {data['title']}")
            else:
                for key, value in fields.items():
                    setattr(existing, key, value)
                updated.append(f"{data['sequence']}. {data['title']}")

        await session.commit()

        if inserted:
            print(f"Insertados {len(inserted)} módulos nuevos en A1: " + ", ".join(inserted))
        if updated:
            print(f"Sincronizados {len(updated)} módulos ya existentes en A1: " + ", ".join(updated))
        total_hours = sum(m["estimated_hours"] for m in A1_MODULES)
        print(f"Total A1: {len(A1_MODULES)} módulos, {total_hours}h.")


if __name__ == "__main__":
    asyncio.run(seed_a1_modules())
