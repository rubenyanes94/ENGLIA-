from pydantic import BaseModel


class PronunciationFeedbackOut(BaseModel):
    """Lo que el alumno recibe tras grabarse.

    `transcript` se devuelve a propósito aunque no sea "la nota": ver
    escrito lo que el modelo OYÓ es la parte más útil del ejercicio. Un
    "78/100" no enseña nada; leer "I have twenty five years" cuando
    creías haber dicho otra cosa, sí.
    """

    expected: str
    transcript: str
    matches: bool
    score: int
    feedback_es: str
