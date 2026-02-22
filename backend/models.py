from datetime import datetime
import enum
from typing import Optional
from sqlalchemy import Boolean, String, Text, Float, DateTime, ForeignKey, Enum as sqlalchemy_Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

class EmailStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("monitored_accounts.id"), nullable=True)
    sender: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    status: Mapped[EmailStatus] = mapped_column(
        sqlalchemy_Enum(EmailStatus), 
        default=EmailStatus.PENDING,
        nullable=False
    )
    
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped["Analysis"] = relationship(
        back_populates="email", cascade="all, delete-orphan", uselist=False
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"))
    
    # ML Outputs
    priority_score: Mapped[float] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    email: Mapped["Email"] = relationship(back_populates="analysis")

class MonitoredAccount(Base):
    __tablename__ = "monitored_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email_address: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    imap_server: Mapped[str] = mapped_column(String(255), default="imap.gmail.com")
    password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)