import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Descriptor(Base):
    """Catálogo de descriptores MCER ("can-do") de un nivel — la unidad
    ATÓMICA de progreso del currículo (documento de diseño § 1.6), distinta
    de Module: un módulo AGRUPA descriptores, pero el dominio se mide
    descriptor por descriptor (ver DescriptorEvidence).

    Se siembra por script desde el documento DESCRIPTORS de cada nivel
    (ver app/scripts/seed_a1_descriptors.py); no tiene formulario de
    autoría todavía, igual que el contenido rico de Module.
    """

    __tablename__ = "descriptors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cefr_levels.id"))

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # "A1.LI.01"
    # Nombre de destreza en texto (listening, spoken_interaction,
    # phonology...) — más descriptivo que el modo de 2 letras embebido en
    # `code`; viene tal cual del documento fuente (campo `skill`).
    skill: Mapped[str] = mapped_column(String(30))

    statement_en: Mapped[str] = mapped_column(Text)
    statement_es: Mapped[str] = mapped_column(Text)

    # Códigos de Module (o el sentinel "all" para descriptores
    # transversales, ej. fonología general o alcance léxico) donde este
    # descriptor se desarrolla. Sin FK, misma razón que Module.recycles.
    modules: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # "critical" o None. Los descriptores critical son los que bloquean la
    # salida de nivel (ver Module.assessment.level_exit_criteria de a1-10).
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # True si el descriptor existe específicamente por interferencia L1
    # de un hispanohablante (ej. epéntesis, sujeto nulo) — distingue "MCER
    # genérico" de "lo que este currículo añade para este perfil de alumno".
    l1_specific: Mapped[bool] = mapped_column(Boolean, default=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Meta cuantitativa suelta cuando aplica (ej. "~600 unidades activas al
    # cierre de A1" en A1.LX.01) — texto libre, no todos los descriptores lo tienen.
    target: Mapped[str | None] = mapped_column(String(100), nullable=True)

    level: Mapped["CEFRLevel"] = relationship()

    def __repr__(self) -> str:
        return f"<Descriptor {self.code}>"


class DescriptorEvidence(Base):
    """Un registro de "ejecución exitosa" de un alumno sobre un
    descriptor — el ladrillo con el que se acumula `descriptor_mastery`
    (documento § 1.6), NUNCA una nota aislada.

    Por qué existe esta tabla y no basta con ExerciseAttempt: la regla de
    dominio exige que las evidencias ocurran en CONTEXTOS distintos y
    SESIONES distintas, y un mismo descriptor puede evidenciarse desde
    fuentes distintas (un ejercicio calificado hoy, una tarea de chat con
    el tutor el día de mañana) — se necesita una tabla propia, agnóstica
    de la fuente, para poder contarlas juntas.
    """

    __tablename__ = "descriptor_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    # Referencia por código (no FK a Descriptor.id): así sembrar de nuevo
    # el catálogo (ej. tras corregir un statement) nunca invalida evidencia
    # ya registrada, y una evidencia puede registrarse aunque el catálogo
    # de ese nivel todavía no exista.
    descriptor_code: Mapped[str] = mapped_column(String(20), index=True)

    # Identifica el "contexto" distinto que exige la regla de dominio (ej.
    # el id del exercise/task concreto). Repetir el MISMO contexto no debe
    # poder contar dos veces como evidencia distinta.
    context: Mapped[str] = mapped_column(String(255))

    # Identifica la "sesión" distinta que exige la regla. Para evidencia
    # de chat (pendiente de cablear) será el id de ConversationSession;
    # para un intento de ejercicio (fuente ya cableada, ver
    # descriptor_evidence_repository) es el id del propio ExerciseAttempt
    # — proxy razonable, NO una sesión de estudio real: Exercise no agrupa
    # intentos en sesiones. Documentado aquí para que quien lo lea no lo
    # confunda con algo más riguroso de lo que es.
    session_key: Mapped[str] = mapped_column(String(255))

    # Si el tutor dio andamiaje directo (ver Module.tutor_config.scaffolds)
    # durante esta ejecución. Un intento de Exercise nunca tiene andamiaje
    # posible (es autocorrección determinista o por IA sin ayuda en vivo),
    # así que las evidencias de esa fuente siempre entran con False.
    scaffolded: Mapped[bool] = mapped_column(Boolean, default=False)

    success: Mapped[bool] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(String(30))  # "exercise_attempt" | "chat_task" | "manual"

    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<DescriptorEvidence {self.descriptor_code} user={self.user_id} success={self.success}>"
