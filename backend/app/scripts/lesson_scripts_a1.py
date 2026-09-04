"""Guiones de las lecciones narradas de A1, escritos a mano.

Por qué a mano y no generados: se intentó con el LLM local (ver
seed_a1_lessons.py) y el modelo de 0.5B que cabe en este entorno produjo
guiones inservibles — listas con viñetas en vez de prosa narrada, frases
repetidas en bucle, preámbulos del tipo "Aquí tienes el guión..." que se
leerían en voz alta, y CERO marcas [[...]], con lo que el inglés se
habría narrado con voz española. En una app de idiomas eso no es un
detalle estético: es enseñar mal.

Cada guión está anclado al currículo real de su módulo (objetivos,
chunks, y sobre todo los errores de interferencia L1 que ese módulo
declara), no a un tema genérico.

Formato: español corrido para narrar, con CADA frase en inglés entre
[[dobles corchetes]] para que Piper la diga con la voz inglesa (ver
app/media/piper_tts.py).
"""

# Clave: Module.code
LESSON_SCRIPTS: dict[str, str] = {
    "A1.M01": (
        "Hola, bienvenido a tu primera lección. Hoy vas a aprender a presentarte en inglés, y sobre "
        "todo a evitar dos errores que casi todos los hispanohablantes cometemos. "
        "Empecemos por saludar. Por la mañana decimos [[Good morning]]. Por la tarde, "
        "[[Good afternoon]]. Y al despedirte, basta con [[Goodbye]], o simplemente [[Bye]]. "
        "Ahora vamos a presentarnos. La fórmula que quiero que memorices completa, sin analizarla, "
        "es esta: [[My name's Ana and I'm from Colombia]]. Repítela conmigo: "
        "[[My name's Ana and I'm from Colombia]]. "
        "Y aquí viene el primer error. En español decimos tengo veinticinco años, con el verbo tener. "
        "En inglés no se usa tener: se usa el verbo ser. Se dice [[I'm 25]]. Nunca digas "
        "[[I have 25 years]]: es un calco del español y se nota muchísimo. Repite conmigo: [[I'm 25]]. "
        "El segundo error es con tu profesión. En español decimos soy médico, sin artículo. En inglés "
        "siempre lleva artículo delante: [[I'm a doctor]], [[I'm a student]], [[I'm an engineer]]. "
        "Repite: [[I'm a doctor]]. "
        "Y una última cosa, quizá la más importante de esta lección: cuando no entiendas algo, no te "
        "quedes callado. Di [[Sorry, can you repeat that?]], o [[Can you speak more slowly, please?]]. "
        "Esa frase te va a salvar mil conversaciones. "
        "Para terminar, cuando conozcas a alguien: [[Nice to meet you]]. Repite: [[Nice to meet you]]. "
        "Nos vemos en la práctica con tu tutor."
    ),
}
