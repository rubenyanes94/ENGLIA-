import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExerciseOut(BaseModel):
    """OJO: a propósito NO incluye `answer_key`. Este schema es lo que ve
    el alumno al abrir una lección — exponer la clave de respuestas aquí
    dejaría que cualquiera la lea directamente desde la pestaña Network
    del navegador, antes incluso de intentar el ejercicio."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_type: str
    stage: str  # "practice" | "exam" — así el frontend sabe en qué pestaña pintarlo
    prompt: str


class ExerciseAdminOut(ExerciseOut):
    """A diferencia de ExerciseOut, esta SÍ incluye `answer_key` — es lo
    que ve un admin gestionando contenido, nunca lo que ve un alumno."""

    answer_key: dict


class ExerciseCreate(BaseModel):
    exercise_type: str
    stage: str = "practice"
    prompt: str
    answer_key: dict = {}


class ExerciseUpdate(BaseModel):
    exercise_type: str | None = None
    stage: str | None = None
    prompt: str | None = None
    answer_key: dict | None = None


class SubmitExerciseAttemptRequest(BaseModel):
    """Un único campo `answer` para los cuatro tipos de ejercicio: la
    opción elegida (multiple_choice), la palabra escrita (fill_blank), o
    el texto libre (writing/speaking). Mantiene el contrato simple para
    el frontend; la variación por tipo se resuelve del lado del agente
    (app/agents/grading.py), no aquí."""

    answer: str


class ExerciseAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID
    score: float
    ai_feedback: str | None
    attempted_at: datetime
