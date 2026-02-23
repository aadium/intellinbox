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

class InboxBase(BaseModel):
    email_address: str
    imap_server: str = "imap.gmail.com"
    is_active: bool = True

class InboxCreate(InboxBase):
    password: str

class InboxRead(InboxBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EmailBase(BaseModel):
    sender: str
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
    inbox: Optional[InboxRead] = None

    model_config = ConfigDict(from_attributes=True)