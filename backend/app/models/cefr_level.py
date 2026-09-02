import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class CEFRLevel(Base):
    """Catálogo FIJO de los 6 niveles del Marco Común Europeo de Referencia
    (A1, A2, B1, B2, C1, C2). Se siembra una única vez; no lo edita el usuario."""

    __tablename__ = "cefr_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(2), unique=True, index=True)  # "A1".."C2"
    name: Mapped[str] = mapped_column(String(50))  # "Acceso", "Plataforma", "Maestría"...
    order: Mapped[int] = mapped_column(Integer, unique=True)  # 1..6, define la progresión
    description: Mapped[str] = mapped_column(Text)

    # `level_policy` del documento de currículo: techo de lenguaje del
    # tutor ({"allowed": [...], "forbidden": [...]}), velocidad de habla,
    # léxico nuevo máx. por sesión, política de apoyo en L1 y jerarquía de
    # corrección — heredado por TODOS los módulos del nivel salvo que su
    # propio `tutor_config` lo sobreescriba. Vive aquí (no en AgentPersona)
    # porque describe el NIVEL, no un tutor concreto. Se compone en el
    # system prompt real del chat vía app.agents.prompt_builder.
    tutor_policy: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Regla de dominio de descriptor (documento § 1.6): {"threshold": 0.8,
    # "evidence_required": 3, "conditions": [...]}. Vive aquí (no en cada
    # Descriptor) porque es una política uniforme para TODOS los
    # descriptores del nivel — ver descriptor_evidence_repository.compute_mastery.
    mastery_rule: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Versión EJECUTABLE de los `level_exit_criteria` en texto libre que
    # declara el módulo de cierre del nivel (Module.assessment) — ese
    # texto es para LEER, este dict es para EVALUAR. Estructura:
    # {"descriptor_mastery_ratio": {"min_ratio": 0.8, "min_mastery": 0.7},
    #  "exit_tasks": [{"task_id": "a1-10-t2", "times_required": 2}]}
    # El criterio "todos los descriptores critical dominados" NO necesita
    # parámetros aquí: se deriva de Descriptor.priority=="critical" +
    # mastery_rule.threshold — ver descriptor_evidence_repository.evaluate_level_exit_gate.
    exit_gate: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Horas de aprendizaje guiado para certificar este nivel (ej. A1:
    # 80-150h, según el marco de referencia habitual). Es un rango, no un
    # número fijo, porque depende de la intensidad del alumno — el
    # "% de progreso" que se muestra en el dashboard se calcula contra
    # target_hours_max (ver levels.get_certification_progress), así que
    # nunca llega a 100% prematuramente en el extremo bajo del rango.
    target_hours_min: Mapped[int] = mapped_column(Integer, default=80)
    target_hours_max: Mapped[int] = mapped_column(Integer, default=150)

    modules: Mapped[list["Module"]] = relationship(back_populates="level")
    personas: Mapped[list["AgentPersona"]] = relationship(back_populates="level")

    def __repr__(self) -> str:
        return f"<CEFRLevel {self.code}>"
