import os

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from security import encrypt_password

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))

router = APIRouter(
    prefix="/inboxes",
    tags=["Inboxes"]
)

@router.get("/", response_model=List[schemas.InboxRead])
def read_inboxes(db: Session = Depends(get_db)):
    return db.query(models.MonitoredInbox).all()

@router.post("/", response_model=schemas.InboxRead)
def create_inbox(inbox: schemas.InboxCreate, db: Session = Depends(get_db), sync_days: int = 30):
    existing = db.query(models.MonitoredInbox).filter(
        models.MonitoredInbox.email_address == inbox.email_address
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already being monitored")

    db_inbox = models.MonitoredInbox(
        email_address=inbox.email_address,
        imap_server=inbox.imap_server,
        password=encrypt_password(inbox.password),
        is_active=inbox.is_active
    )
    db.add(db_inbox)
    db.commit()
    db.refresh(db_inbox)
    celery_app.send_task("tasks.setup_inbox", args=[db_inbox.id, sync_days])
    return db_inbox

@router.post("/{inbox_id}/reset")
def flush_inbox(inbox_id: int, db: Session = Depends(get_db), sync_days: int = 30):
    inbox = db.query(models.MonitoredInbox).filter(models.MonitoredInbox.id == inbox_id).first()
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    db.query(models.Analysis).filter(
        models.Analysis.email_id.in_(
            db.query(models.Email.id).filter(models.Email.inbox_id == inbox_id)
        )
    ).delete(synchronize_session=False)
    db.query(models.Email).filter(models.Email.inbox_id == inbox_id).delete()
    db.commit()
    celery_app.send_task("tasks.setup_inbox", args=[inbox_id, sync_days])
    return {"message": "Reset task started in background"}

@router.post("/{inbox_id}/sync")
def trigger_sync(inbox_id: int, db: Session = Depends(get_db)):
    inbox = db.query(models.MonitoredInbox).filter(models.MonitoredInbox.id == inbox_id).first()
    if not inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    celery_app.send_task("tasks.sync_inbox", args=[inbox_id])
    return {"message": "Sync task started in background"}

@router.post("/syncall")
def sync_all_inboxes(db: Session = Depends(get_db)):
    active_inboxes = db.query(models.MonitoredInbox).filter(models.MonitoredInbox.is_active == True).all()
    
    for inbox in active_inboxes:
        celery_app.send_task("tasks.sync_inbox", args=[inbox.id])
        
    return {"message": f"Sync tasks dispatched for {len(active_inboxes)} inboxes"}

@router.patch("/{inbox_id}/status", response_model=schemas.InboxRead)
def update_inbox_status(inbox_id: int, is_active: bool, db: Session = Depends(get_db)):
    db_inbox = db.query(models.MonitoredInbox).filter(models.MonitoredInbox.id == inbox_id).first()
    if not db_inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    db_inbox.is_active = is_active
    db.commit()
    db.refresh(db_inbox)
    return db_inbox

@router.delete("/{inbox_id}")
def delete_inbox(inbox_id: int, db: Session = Depends(get_db)):
    db_inbox = db.query(models.MonitoredInbox).filter(models.MonitoredInbox.id == inbox_id).first()
    if not db_inbox:
        raise HTTPException(status_code=404, detail="Inbox not found")
    db.delete(db_inbox)
    db.commit()
    return {"detail": "Inbox and associated data deleted"}