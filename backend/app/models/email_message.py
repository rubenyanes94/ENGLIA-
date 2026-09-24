import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class EmailMessage(Base):
    """Un correo que se le envió (o se intentó enviar) a un alumno.

    Existe por tres razones, y la primera es la importante:

    1. **No escribirle dos veces lo mismo.** `dedupe_key` es única por
       usuario: "vence_pronto" del periodo que acaba el 23/10 tiene la
       clave "vence_pronto:2026-10-23". El bucle de retención se ejecuta
       cada hora y vuelve a encontrar al mismo alumno una y otra vez; la
       fila insertada ANTES de llamar a Resend es lo que impide que reciba
       veinticuatro avisos iguales en un día. Nada de "ya lo envié" en
       memoria: si el backend se reinicia, la base sigue sabiéndolo.

    2. **Saber qué pasó.** Resend puede rechazar un envío (dominio sin
       verificar, dirección inválida). Se guarda el estado y el error para
       que el panel de Sistema lo cante en vez de perderse en un log.

    3. **Poder mirarlo desde gerencia**: qué se le ha escrito a un cliente
       y cuándo, sin entrar en la cuenta de Resend.

    No se guarda el HTML: ocupa y se puede volver a generar a partir de
    `kind` y `context`.
    """

    __tablename__ = "email_messages"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_email_messages_user_dedupe"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # El tipo de correo: "bienvenida", "pago_aprobado", "vence_pronto"...
    # (las claves de app/notifications/messages.py).
    kind: Mapped[str] = mapped_column(String(40), index=True)
    # kind + lo que lo hace único en el tiempo. Para los transaccionales
    # es el id del pago; para los de calendario, la fecha a la que se
    # refieren. Ver el docstring de arriba.
    dedupe_key: Mapped[str] = mapped_column(String(120))

    # "sent" | "failed" | "skipped". "skipped" es un envío que no se
    # intentó y por qué (el alumno se dio de baja, no hay API key): sin
    # esta fila, el bucle lo reintentaría cada hora para siempre.
    status: Mapped[str] = mapped_column(String(20), default="sent", index=True)
    to_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    # El id que devuelve Resend, para cruzar con su panel si hace falta.
    provider_message_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lo que se usó para rellenar la plantilla (nombre, fecha de
    # vencimiento, motivo del rechazo...).
    context: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<EmailMessage {self.kind} {self.to_email} {self.status}>"
