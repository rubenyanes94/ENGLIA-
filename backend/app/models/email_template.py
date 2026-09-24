import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base


class EmailTemplate(Base):
    """Un mensaje escrito desde gerencia para enviárselo a un grupo de
    clientes: una promoción, el aviso de un curso nuevo, una felicitación.

    Se guardan los CAMPOS, no el HTML. El correo se arma en el momento de
    enviarlo con la misma plantilla que todos los demás
    (app/notifications/layout.py), así que una plantilla escrita hoy se
    verá con el estilo de Espikin de mañana, sin tener que reescribirla.
    Y además no se puede colar HTML arbitrario en un correo que sale a
    nombre de la academia.

    `body` es texto normal: cada párrafo va separado por una línea en
    blanco. En el título y en el cuerpo se puede escribir {nombre} y se
    sustituye por el nombre de pila de cada alumno.
    """

    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Cómo la llama quien la escribió ("Promo de Navidad"). No sale en el
    # correo: es para reconocerla en la lista.
    name: Mapped[str] = mapped_column(String(120))

    subject: Mapped[str] = mapped_column(String(200))
    # La línea que se lee junto al asunto en la bandeja de entrada.
    preheader: Mapped[str] = mapped_column(String(200), default="")
    # La etiqueta pequeña de arriba ("Promoción", "Novedad").
    eyebrow: Mapped[str] = mapped_column(String(40), default="Espikin")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)

    # El botón es opcional: hay avisos que no piden ninguna acción.
    button_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name}>"


class EmailCampaign(Base):
    """Un envío concreto de una plantilla a un grupo de clientes.

    Se guarda aparte de email_templates porque una plantilla se puede
    enviar varias veces (a grupos distintos, en meses distintos) y porque
    esto es lo que se mira después: a cuántos les llegó, a cuántos no y
    por qué.

    El contenido se copia aquí al enviar (subject/title/body): si alguien
    edita la plantilla el mes que viene, el registro de lo que se mandó en
    enero tiene que seguir diciendo lo que se mandó en enero.
    """

    __tablename__ = "email_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(200))
    # Copia del contenido tal como se envió (asunto, título, cuerpo,
    # botón). Ver el docstring: la plantilla puede cambiar después.
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    # La clave del grupo al que se envió ("por_vencer", "inactivos"...),
    # ver app/notifications/audiences.py.
    audience: Mapped[str] = mapped_column(String(40))

    # "enviando" | "terminada". Un envío a 200 personas tarda un minuto
    # largo y ocurre en segundo plano: el panel enseña el avance.
    status: Mapped[str] = mapped_column(String(20), default="enviando", index=True)
    # Cuántos había en el grupo cuando se lanzó.
    recipients: Mapped[int] = mapped_column(default=0)
    sent: Mapped[int] = mapped_column(default=0)
    # Los que no recibieron: dados de baja, direcciones de prueba.
    skipped: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)

    sent_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<EmailCampaign {self.name} → {self.audience}>"
