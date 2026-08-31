# Importar todos los modelos aquí es importante, no decorativo: Alembic
# (autogenerate) y SQLAlchemy (resolución de relationships por nombre de
# clase) necesitan que cada modelo se haya "registrado" contra Base antes
# de comparar metadatos o de configurar los mappers.

from app.models.agent_persona import AgentPersona
from app.models.cefr_level import CEFRLevel
from app.models.conversation import ConversationMessage, ConversationSession
from app.models.enrollment import Enrollment
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User

__all__ = [
    "AgentPersona",
    "CEFRLevel",
    "ConversationMessage",
    "ConversationSession",
    "Enrollment",
    "Exercise",
    "ExerciseAttempt",
    "Lesson",
    "Module",
    "User",
]
