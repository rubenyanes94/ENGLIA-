import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    status: str
    mastery_score: float
    started_at: datetime | None
    completed_at: datetime | None
