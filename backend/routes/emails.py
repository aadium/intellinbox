from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from celery import Celery
import os

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))

router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)

@router.get("/", response_model=List[schemas.EmailRead])
def read_emails(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    emails = db.query(models.Email).order_by(models.Email.received_at.desc()).offset(skip).limit(limit).all()
    return emails

@router.get("/{email_id}", response_model=schemas.EmailRead)
def read_single_email(email_id: int, db: Session = Depends(get_db)):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if db_email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return db_email

@router.post("/", response_model=schemas.EmailRead)
def create_email(email: schemas.EmailCreate, db: Session = Depends(get_db)):
    db_email = models.Email(
        sender=email.sender,
        subject=email.subject,
        body=email.body
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    celery_app.send_task("tasks.analyze_email", args=[db_email.id])
    return db_email

@router.patch("/{email_id}/analysis", response_model=schemas.AnalysisRead)
def update_email_analysis(
    email_id: int,
    db: Session = Depends(get_db)
):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not db_email:
        raise HTTPException(status_code=404, detail="Email not found")
    db_email.status = models.EmailStatus.PROCESSING
    db.commit()
    db.refresh(db_email)
    db.delete(db_email.analysis)
    db.commit()
    celery_app.send_task("tasks.analyze_email", args=[db_email.id])
    return db_email.analysis

@router.delete("/{email_id}", response_model=schemas.EmailDelete)
def delete_email(email_id: int, db: Session = Depends(get_db)):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not db_email:
        raise HTTPException(status_code=404, detail="Email not found")
    db.delete(db_email)
    db.commit()
    return db_email