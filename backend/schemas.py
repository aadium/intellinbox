from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

from models import EmailStatus

class AnalysisBase(BaseModel):
    priority_score: Optional[float] = None
    summary: Optional[str] = None
    category: Optional[str] = None

class AnalysisRead(AnalysisBase):
    id: int
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmailBase(BaseModel):
    sender: str
    receiver: str
    subject: str
    body: str

class EmailCreate(EmailBase):
    pass

class EmailDelete(EmailBase):
    id: int
    deleted: bool = True

class EmailRead(EmailBase):
    id: int
    status: EmailStatus
    received_at: datetime
    analysis: Optional[AnalysisRead] = None

    model_config = ConfigDict(from_attributes=True)