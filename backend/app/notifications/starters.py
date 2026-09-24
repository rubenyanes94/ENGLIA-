"""Mensajes ya escritos para arrancar una campaña, en vez de una página
en blanco.

Quien entra a "escribir a los clientes" casi nunca tiene el problema de
no saber QUÉ decir: tiene el de no querer redactarlo desde cero un
martes por la tarde. Estos son los seis motivos por los que una academia
escribe de verdad, cada uno con su texto completo, listo para enviar tal
cual o para cambiarle dos frases.

Cada uno trae `audience`: el grupo al que tiene sentido mandarlo. El
panel lo deja preseleccionado, que es donde más se equivoca uno —
mandarle "renueva antes de que venza" a quien ya renovó.

No son plantillas guardadas: son el punto de partida. En cuanto se
elige uno, lo que se edita y se guarda es una plantilla normal y
corriente del usuario, y estos textos no vuelven a tocarse.

Sobre cómo están escritos:

- Van en segunda persona y sin regaño. "Hace días que no pasas por el
  aula" retiene; "no has cumplido tu objetivo" hace que te marquen como
  spam.
- Llevan {nombre} y *asteriscos* ya puestos, porque son justo las dos
  cosas que nadie descubre solo.
- Los que dependen de algo que solo sabe la academia (qué novedad se
  está anunciando) llevan el hueco entre corchetes bien visible: es
  mejor un [di aquí qué es lo nuevo] que un párrafo genérico que se
  enviaría sin darse cuenta.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Starter:
    key: str
    label: str
    description: str
    # El grupo de app/notifications/audiences.py que el panel deja
    # preseleccionado al elegir este mensaje.
    audience: str
    name: str
    subject: str
    preheader: str
    eyebrow: str
    title: str
    body: str
    button_label: str


STARTERS: list[Starter] = [
    Starter(
        key="oferta",
        label="Promoción o descuento",
        description="Un regalo con fecha límite para que quien se fue vuelva ahora y no “algún día”.",
        audience="vencidos",
        name="Promoción",
        subject="Una semana de regalo, {nombre}",
        preheader="Renueva antes del domingo y te sumamos siete días.",
        eyebrow="Promoción",
        title="Te regalamos *una semana*, {nombre}",
        body=(
            "Aprender un idioma se corta con una facilidad tremenda: una semana ocupada y ya no vuelves. "
            "Lo vemos todos los meses y por eso te escribimos.\n\n"
            "Si renuevas antes del domingo, te sumamos *siete días extra* sin costo. "
            "Sigues justo donde lo dejaste, con tu mismo nivel y tu mismo tutor."
        ),
        button_label="Quiero mi semana extra",
    ),
    Starter(
        key="renovar",
        label="Empujón a renovar",
        description="Para quien está a días de quedarse sin acceso y todavía no ha pagado.",
        audience="por_vencer",
        name="Recordatorio de renovación",
        subject="No pierdas el hilo, {nombre}",
        preheader="Tu acceso está por terminar. Renovar toma dos minutos.",
        eyebrow="Tu suscripción",
        title="Te quedan *pocos días*, {nombre}",
        body=(
            "Tu acceso a Espikin está por terminar. Renovando ahora no se interrumpe nada: "
            "ni tu racha, ni el trabajo que vienes haciendo con tu tutor.\n\n"
            "Son dos minutos desde tu perfil y sigues igual que hoy."
        ),
        button_label="Renovar mi acceso",
    ),
    Starter(
        key="volver",
        label="Recuperar a quien se fue",
        description="Recordarle que su progreso sigue intacto: volver no es empezar de cero.",
        audience="vencidos",
        name="Te esperamos de vuelta",
        subject="Tu progreso sigue aquí, {nombre}",
        preheader="Tu nivel y tus módulos siguen guardados como los dejaste.",
        eyebrow="Te esperamos",
        title="*Nada se ha borrado*, {nombre}",
        body=(
            "Tu nivel, tus módulos y todo lo que trabajaste siguen guardados exactamente como los dejaste.\n\n"
            "Volver no es empezar de cero: es retomar la conversación donde se quedó. "
            "Tu tutor se acuerda de en qué andabas."
        ),
        button_label="Retomar mis clases",
    ),
    Starter(
        key="primer_pago",
        label="Convencer al que no ha pagado",
        description="Se registró y ahí se quedó. Lo que cuesta es el primer día, no el precio.",
        audience="nunca_pagaron",
        name="Tu primera clase",
        subject="Tu primera clase te está esperando",
        preheader="Cinco minutos de conversación y sabrás tu nivel real.",
        eyebrow="Empieza hoy",
        title="Cinco minutos y *sabrás tu nivel*, {nombre}",
        body=(
            "Creaste tu cuenta pero todavía no has hablado con ningún tutor. "
            "Es lo que más cuesta de todo esto, y a la vez lo que menos tiempo toma.\n\n"
            "Con *cinco minutos de conversación* ya sabemos por dónde empezar contigo, "
            "y tú sabes cuánto inglés tienes de verdad. Sin examen y sin vergüenza: "
            "el tutor está para corregirte, no para juzgarte."
        ),
        button_label="Activar mi acceso",
    ),
    Starter(
        key="practicar",
        label="Despertar a quien no entra",
        description="Paga pero lleva días sin aparecer. Son los que no renuevan el mes que viene.",
        audience="inactivos",
        name="Vuelve a practicar",
        subject="Diez minutos hoy, {nombre}",
        preheader="Diez minutos hoy valen más que dos horas el domingo.",
        eyebrow="Tu práctica",
        title="Diez minutos hoy *valen más* que dos horas el domingo",
        body=(
            "Hace días que no pasas por el aula, {nombre}, y lo decimos sin regaño: "
            "aprender un idioma va de constancia, no de maratones.\n\n"
            "Tu tutor retoma la conversación donde la dejaron. No hace falta que prepares nada."
        ),
        button_label="Practicar ahora",
    ),
    Starter(
        key="novedad",
        label="Contar algo nuevo",
        description="Un curso, una función, un tutor. Rellena los corchetes y listo.",
        audience="con_acceso",
        name="Novedad en Espikin",
        subject="Novedad en Espikin, {nombre}",
        preheader="[Una línea que dé ganas de abrirlo]",
        eyebrow="Novedad",
        title="Ya puedes *[lo nuevo]*, {nombre}",
        body=(
            "[Cuenta en una frase qué acabas de añadir: un curso, una función, un tutor nuevo.]\n\n"
            "[Y en otra, qué gana el alumno con eso. Lo que le pasa a él, no lo que hicimos nosotros.]"
        ),
        button_label="Verlo en la app",
    ),
]

BY_KEY = {s.key: s for s in STARTERS}


def as_dicts() -> list[dict]:
    return [asdict(s) for s in STARTERS]
