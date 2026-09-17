from pydantic import BaseModel


class GameStateOut(BaseModel):
    level: int
    max_level: int
    level_name: str
    level_topic: str
    level_progress: int
    level_goal: int
    total_answered: int
    total_correct: int
    streak: int
    best_streak: int


class GameItemOut(BaseModel):
    """La oración a completar. Sin la respuesta: se corrige en el servidor."""

    id: str
    sentence: str
    options: list[str]


class GameNextOut(BaseModel):
    item: GameItemOut
    state: GameStateOut


class GameAnswerIn(BaseModel):
    item_id: str
    answer: str


class GameAnswerOut(BaseModel):
    correct: bool
    # Se devuelve tras responder, no antes: es un juego de práctica, y ver
    # la correcta junto a la explicación es lo que enseña.
    correct_answer: str
    explanation_es: str
    leveled_up: bool
    state: GameStateOut
