from pydantic import BaseModel


class FlashCourseSummaryOut(BaseModel):
    slug: str
    title: str
    title_es: str
    description_es: str
    category: str
    icon: str
    recommended_level: str
    duration_minutes: int
    scenario_count: int
    completed_scenarios: int
    completed: bool


class KeyPhraseOut(BaseModel):
    en: str
    es: str


class ScenarioOut(BaseModel):
    """Lo que el alumno ve de un escenario. No incluye `success_criteria`:
    es la vara con la que el tutor evalúa, no una instrucción para el
    alumno, y leída de antemano se convierte en una lista de frases que
    recitar para aprobar."""

    id: str
    title: str
    prompt: str
    tutor_role: str
    completed: bool


class FlashCourseDetailOut(FlashCourseSummaryOut):
    communicative_objectives: list[str]
    key_phrases: list[KeyPhraseOut]
    scenarios: list[ScenarioOut]
