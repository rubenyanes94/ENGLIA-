import uuid

from pydantic import BaseModel


class ExamQuestionOut(BaseModel):
    """Una pregunta tal como la ve el alumno.

    Las opciones salen de `answer_key["options"]`, pero la respuesta
    correcta (`answer_key["correct"]`) NO se incluye: cualquiera podría
    leerla en la pestaña Network del navegador antes de responder."""

    id: uuid.UUID
    prompt: str
    options: list[str]


class ExamOut(BaseModel):
    module_id: uuid.UUID
    total: int
    pass_count: int
    questions: list[ExamQuestionOut]


class ExamSubmitRequest(BaseModel):
    # id de la pregunta -> texto exacto de la opción elegida.
    answers: dict[str, str]


class ExamReviewItemOut(BaseModel):
    descriptor_code: str
    statement_es: str


class ExamResultOut(BaseModel):
    score: float
    correct: int
    total: int
    pass_count: int
    passed: bool
    module_completed: bool
    # Solo si el módulo quedó completado y hay uno después en el nivel.
    next_module_id: uuid.UUID | None
    # Capacidades que repasar, sacadas de las preguntas falladas. No dice
    # cuál era la respuesta correcta (ver services/module_exam.py).
    review: list[ExamReviewItemOut]
