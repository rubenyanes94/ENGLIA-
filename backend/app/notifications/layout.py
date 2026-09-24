"""La plantilla de los correos de Espikin: una sola, para que todos se
reconozcan como nuestros.

Se escribe como un correo, no como una página web. El HTML de un correo
va veinte años por detrás del de un navegador, así que aquí hay cosas que
en la app serían un error y aquí son obligatorias:

- **Tablas para maquetar.** Outlook (motor de Word) ignora flex, grid y
  buena parte de `float`. Una tabla centrada de 600 px es lo único que se
  ve igual en Gmail, Outlook, Apple Mail y el móvil.
- **Estilos en línea.** Gmail recorta el `<style>` del `<head>` en parte
  de sus clientes; lo único seguro es `style="..."` en cada etiqueta. El
  bloque `<style>` de aquí solo lleva el modo oscuro y el ajuste de
  móvil, que son mejoras: si un cliente los tira, el correo sigue bien.
- **Botón "a prueba de balas".** El bloque VML comentado con `<!--[if
  mso]>` es para Outlook, que no pinta `border-radius` ni el relleno de
  un `<a>`: sin eso, el botón se ve como un enlace suelto.
- **Degradados con color de respaldo.** El `bgcolor` de la celda va
  SIEMPRE y el degradado encima: donde no se pinte (Outlook de
  escritorio) queda el lavanda plano, no un hueco blanco.

El aire es el de la portada (frontend/src/pages/LandingPage.tsx): la
cabecera con el lavado lavanda, la píldora con la etiqueta, un titular
grande con media frase en violeta y un botón de píldora bien gordo. Los
colores y la tipografía salen de frontend/tailwind.config.ts — violeta
brand-600 #6D3BE6 y azul tinta ink-900 #120E3A, con Inter y su respaldo
del sistema (en correo la fuente casi nunca es Inter, así que la pila de
respaldo importa más que en la web).

**El logotipo es el oficial y viaja DENTRO del correo**, adjunto con un
Content-ID (ver resend_client.py y service.py), no enlazado a un
servidor: así se ve aunque no tengamos dominio propio donde alojarlo y no
depende de que una URL siga en pie dentro de seis meses. Como casi todos
los clientes bloquean las imágenes hasta que el lector pulsa "mostrar",
al lado del isotipo va el nombre "Espikin" en TEXTO: con las imágenes
bloqueadas la cabecera se sigue leyendo en vez de quedar el cuadro roto
de siempre. Con EMAIL_LOGO_URL puesta se usa esa URL en lugar del adjunto.
"""

import base64
import re
from dataclasses import dataclass, field
from functools import lru_cache
from html import escape
from pathlib import Path

BRAND = "#6D3BE6"
BRAND_LIGHT = "#F5F2FF"
BRAND_BORDER = "#DCD1FF"
BRAND_WASH = "#EDE7FF"
INK = "#120E3A"
TEXT = "#475569"
MUTED = "#94A3B8"
BORDER = "#E8E4F5"
ALERT = "#E11D48"
ALERT_LIGHT = "#FFF1F4"
ALERT_BORDER = "#FECDD6"
FONT = "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"

LOGO_FILE = Path(__file__).parent / "assets" / "logo-espikin.png"
LOGO_CID = "logo-espikin"

# Solo mejoras: modo oscuro y el ajuste a pantalla estrecha. Va en <style>
# porque son media queries, que no pueden ir en línea.
HEAD_STYLE = """
<style>
  @media (max-width: 620px) {
    .sp-wrap { padding: 16px 10px 28px !important; }
    .sp-head { padding: 22px !important; }
    .sp-card { padding: 26px 22px !important; }
    .sp-title { font-size: 25px !important; }
  }
  @media (prefers-color-scheme: dark) {
    .sp-bg { background: #0A0824 !important; }
    .sp-card { background: #171334 !important; }
    .sp-head { background: #241254 !important; }
    .sp-title, .sp-strong, .sp-word { color: #F5F2FF !important; }
    .sp-text { color: #C9C4E4 !important; }
    .sp-note, .sp-pill { background: #241254 !important; border-color: #3D2184 !important; }
    .sp-foot { color: #8C86AE !important; }
  }
</style>
"""


@lru_cache(maxsize=1)
def logo_base64() -> str:
    """El PNG del logotipo listo para adjuntar. En caché: es el mismo
    archivo en todos los correos y si no se leería del disco en cada envío."""
    return base64.b64encode(LOGO_FILE.read_bytes()).decode()


@dataclass
class Button:
    label: str
    url: str


@dataclass
class Note:
    """El recuadro con el dato concreto del correo: la fecha de
    vencimiento, el monto, el motivo de un rechazo."""

    label: str
    value: str


@dataclass
class Email:
    """Un correo de Espikin ya escrito, listo para enviar."""

    subject: str
    # La línea que el cliente de correo enseña junto al asunto en la
    # bandeja de entrada. Es lo que decide si lo abren: se escribe a mano
    # y no se deja que el cliente coja el principio del texto.
    preheader: str
    # La píldora violeta de arriba. Hace que el correo se lea de un
    # vistazo, como el nombre de la app en una notificación del móvil.
    eyebrow: str
    title: str
    paragraphs: list[str]
    button: Button | None = None
    note: Note | None = None
    # Texto pequeño bajo el botón ("Si ya pagaste, no hace falta que
    # hagas nada").
    footnote: str | None = None
    tone: str = "brand"  # "brand" | "alert": el color de la píldora y del recuadro
    # Aviso en ámbar por ENCIMA del correo, fuera de la tarjeta: hoy solo
    # el del modo de pruebas. Va aparte y no como primer párrafo para no
    # ensuciar el diseño de lo que se está revisando.
    banner: str | None = None
    context: dict = field(default_factory=dict)


def _accent(tone: str) -> str:
    return ALERT if tone == "alert" else BRAND


_EMPHASIS = re.compile(r"\*([^*]+)\*")


def _rich(texto: str, tone: str = "brand") -> str:
    """*así* → así, en violeta. Es la única marca que se puede escribir
    dentro de un texto, y existe porque el titular de la portada también
    lleva media frase en color: es lo que hace que un correo nuestro se
    vea nuestro. Se aplica DESPUÉS de escapar, así que no abre ninguna
    puerta a colar HTML."""
    return _EMPHASIS.sub(rf'<span style="color:{_accent(tone)};">\1</span>', texto)


def _logo_html(logo_url: str | None) -> str:
    src = logo_url or f"cid:{LOGO_CID}"
    return f"""
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="vertical-align:middle;">
                  <img src="{escape(src, quote=True)}" width="38" height="38" alt="Espikin"
                       style="display:block;width:38px;height:38px;border:0;outline:none;text-decoration:none;">
                </td>
                <td class="sp-word" style="padding-left:11px;vertical-align:middle;font-family:{FONT};font-size:21px;font-weight:800;letter-spacing:-.02em;color:{INK};">Espikin</td>
              </tr>
            </table>"""


def _button_html(button: Button) -> str:
    # El botón va SIEMPRE en violeta de marca, incluso en un correo de
    # aviso: el titular ya dice que algo va mal, y lo que el botón ofrece
    # ("reportar el pago otra vez") es la salida, no el problema. Un botón
    # rojo ahí se lee como "no toques esto".
    url = escape(button.url, quote=True)
    label = escape(button.label)
    # El comentario condicional es para Outlook y solo Outlook: el resto
    # de clientes lo ven como un comentario HTML y lo ignoran.
    return f"""
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:30px 0 4px;">
                <tr><td align="center" bgcolor="{BRAND}" style="border-radius:999px;">
                  <!--[if mso]>
                  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
                    href="{url}" style="height:54px;v-text-anchor:middle;width:320px;" arcsize="50%" stroke="f" fillcolor="{BRAND}">
                    <w:anchorlock/><center style="color:#ffffff;font-family:Arial,sans-serif;font-size:17px;font-weight:bold;">{label}</center>
                  </v:roundrect>
                  <![endif]-->
                  <!--[if !mso]><!-- -->
                  <a href="{url}" style="display:inline-block;padding:16px 40px;font-family:{FONT};font-size:17px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:999px;background:{BRAND};">{label}</a>
                  <!--<![endif]-->
                </td></tr>
              </table>"""


def _note_html(note: Note, tone: str) -> str:
    fondo, borde = (ALERT_LIGHT, ALERT_BORDER) if tone == "alert" else (BRAND_LIGHT, BRAND_BORDER)
    return f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:26px 0 4px;">
                <tr><td class="sp-note" bgcolor="{fondo}" style="background:{fondo};border:1px solid {borde};border-radius:18px;padding:18px 22px;">
                  <p style="margin:0;font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:{_accent(tone)};">{escape(note.label)}</p>
                  <p class="sp-strong" style="margin:7px 0 0;font-family:{FONT};font-size:21px;font-weight:800;letter-spacing:-.01em;color:{INK};">{escape(note.value)}</p>
                </td></tr>
              </table>"""


def _banner_html(texto: str) -> str:
    return f"""
        <tr><td style="padding-bottom:14px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td bgcolor="#FEF3C7" style="background:#FEF3C7;border:1px solid #FCD34D;border-radius:14px;padding:11px 16px;font-family:{FONT};font-size:13px;line-height:1.5;color:#78350F;">{texto}</td></tr>
          </table>
        </td></tr>"""


def render_html(email: Email, unsubscribe_url: str | None = None, logo_url: str | None = None) -> str:
    """El correo completo. `unsubscribe_url` solo se pasa en los correos
    comerciales: en uno transaccional (un pago rechazado) ofrecer "no
    quiero recibir más" sería ofrecerle dejar de enterarse de su dinero."""
    accent = _accent(email.tone)
    parrafos = "".join(
        f'<p class="sp-text" style="margin:0 0 15px;font-family:{FONT};font-size:16px;line-height:1.7;color:{TEXT};">{_rich(p, email.tone)}</p>'
        for p in email.paragraphs
    )
    boton = _button_html(email.button) if email.button else ""
    nota = _note_html(email.note, email.tone) if email.note else ""
    pie_nota = (
        f'<p class="sp-foot" style="margin:16px 0 0;font-family:{FONT};font-size:13px;line-height:1.6;color:{MUTED};">{email.footnote}</p>'
        if email.footnote
        else ""
    )
    baja = (
        f'<br><a href="{escape(unsubscribe_url, quote=True)}" style="color:{MUTED};text-decoration:underline;">No quiero recibir estos recordatorios</a>'
        if unsubscribe_url
        else ""
    )
    banner = _banner_html(email.banner) if email.banner else ""

    return f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{escape(email.subject)}</title>
{HEAD_STYLE}</head>
<body class="sp-bg" style="margin:0;padding:0;background:#F1F0F7;">
  <!-- Preheader: lo que se lee junto al asunto en la bandeja. Oculto en el
       cuerpo; los espacios de después evitan que el cliente rellene con el
       principio del texto. -->
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(email.preheader)}
    &#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="sp-bg" style="background:#F1F0F7;">
    <tr><td class="sp-wrap" align="center" style="padding:30px 16px 40px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
        {banner}
        <tr><td>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid {BORDER};border-radius:24px;overflow:hidden;">

            <!-- Cabecera: el lavado lavanda de la portada -->
            <tr><td class="sp-head" bgcolor="{BRAND_WASH}"
                    style="background:{BRAND_WASH};background-image:linear-gradient(120deg,{BRAND_WASH} 0%,#F7F4FF 58%,#FFFFFF 100%);padding:26px 34px;">
              {_logo_html(logo_url)}
            </td></tr>

            <!-- Mensaje -->
            <tr><td class="sp-card" bgcolor="#FFFFFF" style="background:#FFFFFF;padding:34px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px;">
                <tr><td class="sp-pill" bgcolor="{BRAND_LIGHT}" style="background:{BRAND_LIGHT};border:1px solid {BRAND_BORDER};border-radius:999px;padding:7px 15px;font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{accent};">{escape(email.eyebrow)}</td></tr>
              </table>
              <h1 class="sp-title" style="margin:0 0 18px;font-family:{FONT};font-size:30px;line-height:1.22;font-weight:800;letter-spacing:-.025em;color:{INK};">{_rich(escape(email.title), email.tone)}</h1>
              {parrafos}
              {nota}
              {boton}
              {pie_nota}
            </td></tr>

          </table>
        </td></tr>

        <!-- Pie -->
        <tr><td align="center" style="padding:24px 12px 0;">
          <p class="sp-foot" style="margin:0;font-family:{FONT};font-size:12px;line-height:1.75;color:{MUTED};">
            <strong style="color:{MUTED};">Espikin</strong> · Tu academia de inglés con tutores de inteligencia artificial<br>
            Recibes este correo porque tienes una cuenta en Espikin.{baja}
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


def render_text(email: Email, unsubscribe_url: str | None = None) -> str:
    """Versión en texto plano. No es opcional: un correo solo-HTML puntúa
    peor en los filtros de spam, y algunos clientes (relojes, lectores de
    pantalla, avisos del móvil) enseñan esto y no el HTML."""
    lineas = []
    if email.banner:
        lineas += [_strip_tags(email.banner), ""]
    lineas += [_strip_tags(email.title), "", *[_strip_tags(p) for p in email.paragraphs]]
    if email.note:
        lineas += ["", f"{email.note.label}: {email.note.value}"]
    if email.button:
        lineas += ["", f"{email.button.label}: {email.button.url}"]
    if email.footnote:
        lineas += ["", _strip_tags(email.footnote)]
    lineas += ["", "—", "Espikin · Tu academia de inglés con tutores de inteligencia artificial"]
    if unsubscribe_url:
        lineas += [f"Para no recibir estos recordatorios: {unsubscribe_url}"]
    return "\n".join(lineas)


def _strip_tags(html: str) -> str:
    """Los textos llevan algún <strong>, un <a> suelto o los asteriscos del
    énfasis; en texto plano sobra la marca pero no lo que hay dentro."""
    texto = re.sub(r"<br\s*/?>", "\n", html)
    texto = re.sub(r"<[^>]+>", "", texto)
    return _EMPHASIS.sub(r"\1", texto).replace("&nbsp;", " ").strip()
