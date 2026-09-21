import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class ExchangeRate(Base):
    """Tasa oficial del BCV (bolívares por unidad de divisa) para una FECHA
    VALOR concreta.

    Se guarda el historial y no solo "la tasa actual" por dos motivos:
    1. El BCV publica por la tarde la tasa que rige AL DÍA SIGUIENTE. Un
       lunes a las 17:00 su web ya muestra la del martes; quien paga ese
       lunes tiene que pagar con la del lunes. Solo con las fechas valor
       guardadas se puede elegir la que rige hoy (ver app/billing/bcv_rate.py).
    2. Cuando un admin verifica un Pago Móvil necesita saber con qué tasa
       se calculó el monto que vio el alumno.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("currency", "value_date", name="uq_exchange_rates_currency_value_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    # Numeric y no float: el BCV publica 8 decimales y son dinero.
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    value_date: Mapped[date] = mapped_column(Date)
    # "bcv.org.ve" (leída de la web) o "manual" (cargada a mano).
    source: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
