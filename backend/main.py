import os

from celery import Celery
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import engine, SessionLocal, get_db

models.Base.metadata.create_all(bind=engine)

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))

app = FastAPI(title="IntellInbox API")

@app.get("/emails/", response_model=List[schemas.EmailRead])
def read_emails(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    emails = db.query(models.Email).offset(skip).limit(limit).all()
    return emails

@app.get("/emails/{email_id}", response_model=schemas.EmailRead)
def read_single_email(email_id: int, db: Session = Depends(get_db)):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if db_email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return db_email

@app.post("/emails/", response_model=schemas.EmailRead)
def create_email(email: schemas.EmailCreate, db: Session = Depends(get_db)):
    db_email = models.Email(
        sender=email.sender,
        receiver=email.receiver,
        subject=email.subject,
        body=email.body
    )

    db.add(db_email)
    db.commit()
    db.refresh(db_email)

    celery_app.send_task("tasks.analyze", args=[db_email.id])
    
    return db_email

@app.patch("/emails/{email_id}/analysis", response_model=schemas.AnalysisRead)
def update_email_analysis(
    email_id: int, 
    analysis_data: schemas.AnalysisBase, 
    db: Session = Depends(get_db)
):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not db_email:
        raise HTTPException(status_code=404, detail="Email not found")

    if db_email.analysis:
        for key, value in analysis_data.model_dump(exclude_unset=True).items():
            setattr(db_email.analysis, key, value)
    else:
        new_analysis = models.Analysis(**analysis_data.model_dump(), email_id=email_id)
        db.add(new_analysis)

    db_email.status = "completed"
    
    db.commit()
    return db_email.analysis

@app.delete("/emails/{email_id}", response_model=schemas.EmailDelete)
def delete_email(
    email_id = int,
    db: Session = Depends(get_db)
):
    db_email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not db_email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    db.delete(db_email)
    db.commit()
    
    return db_email