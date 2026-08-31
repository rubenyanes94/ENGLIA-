import uuid

from pydantic import BaseModel, ConfigDict


class ExerciseOut(BaseModel):
    """OJO: a propósito NO incluye `answer_key`. Este schema es lo que ve
    el alumno al abrir una lección — exponer la clave de respuestas aquí
    dejaría que cualquiera la lea directamente desde la pestaña Network
    del navegador, antes incluso de intentar el ejercicio."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_type: str
    prompt: str
