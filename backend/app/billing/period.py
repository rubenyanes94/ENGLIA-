"""Cuánto dura un periodo pagado: UN MES DE CALENDARIO que vence a las
12:00 a. m. (medianoche) en hora de Venezuela.

Regla de negocio (no son 30 días fijos):

- Se paga el 15 de enero → el acceso termina el 15 de febrero a las 00:00.
  Como enero tiene 31 días, ese mes pagado duró 31 días.
- Se paga el 5 de febrero → termina el 5 de marzo: 28 días.
- Se paga el 23 de septiembre → termina el 23 de octubre: 30 días.

Es decir: el día en que se paga cuenta entero (aunque se pague a las
11 de la noche) y el acceso se corta en la medianoche del mismo número de
día del mes siguiente. Quien mira su cuenta el último día la ve vigente
hasta que el reloj marca las 12; no se corta a media tarde porque hace un
mes pagó a esa hora.

Dos detalles que conviene tener presentes:

1. **Medianoche de Caracas, no de UTC.** La BD guarda todo en UTC sin zona
   (la convención del resto del backend: datetime.utcnow()), así que aquí
   se pasa a hora local del negocio, se busca la medianoche y se vuelve a
   UTC. En Venezuela son las 04:00 UTC — cortar a las 00:00 UTC dejaría
   sin acceso a las 8 de la noche del día anterior.

2. **Meses cortos.** El 31 de enero no existe en febrero: se recorta al
   último día del mes (28 de febrero, o 29 si es bisiesto). Si después se
   renueva desde ahí, el ancla pasa a ser el 28 — se pierde el "31"
   original. Es la simplificación habitual y evita arrastrar una fecha de
   aniversario aparte; con el cobro manual de hoy (cada mes el alumno
   vuelve a pagar) no cambia nada práctico.
"""

import calendar
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def _business_tz() -> ZoneInfo:
    return ZoneInfo(settings.analytics_timezone)


def add_one_month(day: date) -> date:
    """Mismo número de día del mes siguiente, recortado si ese día no
    existe (31 de enero → 28/29 de febrero)."""
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def period_end(start: datetime) -> datetime:
    """Fin del periodo que empieza en `start`. Entra y sale UTC sin zona.

    Si `start` ya es una medianoche local (renovación encadenada: el
    periodo nuevo arranca justo cuando termina el vigente), el resultado
    es la medianoche del mes siguiente, sin desviarse día a día.
    """
    tz = _business_tz()
    local = start.replace(tzinfo=timezone.utc).astimezone(tz)
    end_local = datetime.combine(add_one_month(local.date()), time.min, tzinfo=tz)
    return end_local.astimezone(timezone.utc).replace(tzinfo=None)
