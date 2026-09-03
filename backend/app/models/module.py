import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Module(Base):
    """Un módulo temático dentro de un nivel MCER (ej.: "Where I live", en A1).

    Los campos desde `code` hasta `tutor_config` reflejan 1:1 la "anatomía
    de un módulo" del documento de diseño curricular (MCER § 3). Van en
    JSONB/ARRAY, no normalizados en tablas propias, por la misma razón que
    `Lesson.content` (ver ese modelo): la fuente de la verdad es un
    documento de currículo versionado que se siembra completo por script,
    no un formulario de admin campo a campo — normalizar cada lista
    (l1_interference, tasks...) en tablas separadas solo tendría sentido el
    día que necesitemos editarlas o consultarlas una a una, no hoy.

    Nullable a propósito en todos los campos nuevos: los niveles A2-C2
    todavía no tienen currículo desarrollado, y un módulo sin estos datos
    debe poder existir (aunque hoy no se siembre ninguno así) sin romper
    el esquema.
    """

    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cefr_levels.id"))

    # Identificador estable del documento de currículo (ej. "A1.M01"),
    # distinto del UUID interno: es lo que usa `recycles` de OTROS módulos
    # para referenciar este, y lo que un admin reconoce al comparar contra
    # el documento fuente. Único pero nullable: los módulos sembrados antes
    # de esta migración (o de niveles sin currículo aún) no tienen uno.
    code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    # Título en español del documento de currículo (distinto de una
    # traducción libre de `title`): el inglés es el nombre "de producto"
    # del módulo, este es el que se le muestra al alumno hispanohablante.
    title_es: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Las 4 destrezas CEFR estándar (listening|speaking|reading|writing) —
    # es la dimensión sobre la que se agrega el desglose de habilidades
    # del alumno (ver enrollment_repository.get_skill_breakdown). Un
    # módulo de gramática o vocabulario se clasifica bajo la destreza que
    # más practica (ej.: gramática de tiempos verbales -> "writing").
    # Con currículo MCER completo (10 modos, no 4 destrezas) esto se deriva
    # en el seed a partir de `descriptors` — ver MODE_TO_SKILL_FOCUS en
    # seed_a1_modules.py — y se guarda ya resuelto, para no obligar al
    # dashboard a conocer el mapeo de modos.
    skill_focus: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer)

    # Códigos de descriptor MCER (ej. "A1.SI.01") que este módulo desarrolla.
    # Referencia por código, no FK a un catálogo `Descriptor`: ese catálogo
    # (con el enunciado "can-do" real de cada descriptor) todavía no existe
    # — solo tenemos los códigos citados dentro de cada módulo, no el
    # documento DESCRIPTORS completo. Ver nota en seed_a1_modules.py.
    descriptors: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Códigos de OTROS módulos (Module.code) cuyo contenido este módulo
    # recicla obligatoriamente (currículo en espiral, MCER § 1.3) — el
    # tutor IA los usa para forzar que reaparezca estructura antigua en
    # contexto nuevo. Sin resolver a FK por la misma razón que `descriptors`.
    recycles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    communicative_objectives: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # {"focus": [...], "note": "..."} — estructuras gramaticales AL
    # SERVICIO de los objetivos comunicativos (MCER § 1.1), no como fin.
    grammar: Mapped[dict] = mapped_column(JSONB, default=dict)

    # {"target_items": int, "sets": [...], "chunks": [...]} — chunks
    # prefabricados aparte de sets léxicos sueltos, a propósito (MCER § 1.4).
    lexis: Mapped[dict] = mapped_column(JSONB, default=dict)

    # {"focus": "...", "l1_alerts": [...]}
    pronunciation: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Lista de {error, target, origin, severity, note?} — el activo
    # diferencial del currículo (MCER § 4): errores anticipados específicos
    # de un hispanohablante en ESTE contenido. Hoy solo se guarda para
    # poder renderizarlo; inyectarlo en el prompt del tutor por turno es
    # trabajo pendiente (requiere que el chat sepa en qué módulo está el
    # alumno — ver chat.py, que hoy solo recibe level_code).
    l1_interference: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Lista de tareas comunicativas evaluables: {id, type, descriptor,
    # prompt, success_criteria?, note?}. Deliberadamente NO son filas de
    # `Exercise`: una `Exercise` es un ítem cerrado/abierto con
    # answer_key/nota numérica (ver exercise.py); una `task` de currículo
    # es una tarea abierta pensada para practicarse EN VIVO con el tutor
    # de chat, no para calificación automática por comparación de texto.
    tasks: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # {"evidence_required": int, "gate_descriptors": [...], "level_exit_criteria"?: [...], "note"?: str}
    assessment: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Contrato de comportamiento del agente IA en ESTE módulo: {"persona",
    # "correction_policy", "scaffolds": [...], "forbidden": [...],
    # "speech_rate"?}. Complementa (no reemplaza) el system_prompt de
    # AgentPersona, que es por NIVEL — esto es la capa por MÓDULO.
    tutor_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # "Peso" en horas de este módulo dentro del total de certificación del
    # nivel (CEFRLevel.target_hours_*). Las horas "certificadas" de un
    # alumno en este módulo = estimated_hours * su mastery_score — es un
    # PROXY del progreso, no tiempo real cronometrado (ver la discusión en
    # enrollment_repository.get_certified_hours): determinista, no se
    # puede inflar dejando una pestaña abierta.
    estimated_hours: Mapped[float] = mapped_column(Float, default=10.0)

    level: Mapped["CEFRLevel"] = relationship(back_populates="modules")
    # order_by aquí (no en cada query): así "lessons" viene ordenado sin
    # importar desde dónde se cargue la relación.
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", order_by="Lesson.order")

    def __repr__(self) -> str:
        return f"<Module {self.title}>"
