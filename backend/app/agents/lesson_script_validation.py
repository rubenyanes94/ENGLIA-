"""Control de calidad de un guión de lección ANTES de narrarlo.

Por qué existe: el modelo produce buenos guiones casi siempre, y de vez
en cuando uno inservible. En la primera tanda de nueve, uno (A1.M06)
escribió todo el inglés SIN las marcas [[...]] — pedagógicamente correcto
pero catastrófico en audio, porque el sintetizador lo habría leído entero
con voz española, enseñando la pronunciación que el alumno viene a
corregir. Otros colaron huecos "___" de ejercicio escrito, que en una
lección que solo se escucha no significan nada.

Revisarlos a mano no escala: cada regeneración habría que releerla
entera. Y el fallo es silencioso — un guión malo se ve perfectamente bien
en la base de datos. La validación convierte "a veces sale mal" en "no
llega al alumno".

Lo que estas comprobaciones NO pueden hacer es juzgar si la lección
enseña bien. Eso sigue necesitando un par de ojos; esto solo ataja los
defectos de FORMA que hacen inútil el audio.
"""

import re

ENGLISH_SEGMENT = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)

# Con límites de palabra a propósito: un "os" suelto casa dentro de
# "vamos", "dos" y "nosotros", y marcaría como peninsular hasta un guión
# escrito a mano en perfecto español latino.
PENINSULAR = re.compile(
    r"\b(vosotros|vuestr\w+|os\s+(?:vais|vais|tenéis|sois)|ordenador\w*|"
    r"móvil(?:es)?|coger|cogéis|zumo|billete(?:s)?|conducir|vale)\b",
    re.IGNORECASE,
)

# Lo que delata que el modelo "pensó en voz alta" o entregó un documento
# en vez de un guión para leer.
REASONING_LEAK = re.compile(r"thinking process|<think|^\s*(?:Aquí tienes|Here\s+is|Here's)\b", re.IGNORECASE | re.MULTILINE)
MARKDOWN = re.compile(r"^\s*[-*#]\s|\*\*", re.MULTILINE)

MIN_ENGLISH_SEGMENTS = 3  # el propio prompt pide "al menos tres ejemplos"
MIN_CHARS = 600


def validate_lesson_script(script: str) -> list[str]:
    """Devuelve la lista de problemas encontrados. Vacía = guión usable."""
    problems: list[str] = []
    text = (script or "").strip()

    if len(text) < MIN_CHARS:
        problems.append(f"demasiado corto ({len(text)} caracteres, mínimo {MIN_CHARS})")

    segments = ENGLISH_SEGMENT.findall(text)
    if len(segments) < MIN_ENGLISH_SEGMENTS:
        problems.append(
            f"solo {len(segments)} frases marcadas con [[...]] (mínimo {MIN_ENGLISH_SEGMENTS}); "
            "sin marcas, el inglés se narraría con voz española"
        )

    if "___" in text:
        problems.append(f"contiene {text.count('___')} hueco(s) '___': no significan nada al escucharlos")

    peninsular = sorted({m.group(0).lower() for m in PENINSULAR.finditer(text)})
    if peninsular:
        problems.append(f"español peninsular: {', '.join(peninsular)}")

    if REASONING_LEAK.search(text):
        problems.append("se coló el razonamiento del modelo o un preámbulo ('Aquí tienes...')")

    if MARKDOWN.search(text):
        problems.append("tiene listas o markdown: es un guión para leer en voz alta, no un documento")

    # Un guión cortado a mitad de frase es lo que pasa cuando el tope de
    # tokens se queda corto (ver settings.lesson_script_max_tokens).
    if text and not text.endswith((".", "!", "?", "…", '"')):
        problems.append(f"no termina en punto — probablemente cortado: ...{text[-45:]!r}")

    return problems
