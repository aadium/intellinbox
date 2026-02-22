import os
import time
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Analysis, Email, EmailStatus

# Celery Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(name="tasks.analyze")
def analyze_email(email_id: int):
    print(f"!!! WORKER ACTIVATED FOR EMAIL ID: {email_id} !!!")
    db = SessionLocal()

    from transformers import pipeline
    print("--- Loading BERT and T5 models ---")
    classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
    summarizer = pipeline("summarization", model="t5-small")
    zero_shot = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    labels = ["critical urgency", "moderate priority", "low priority/backlog"]

    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email: return "Email not found"

        email.status = EmailStatus.PROCESSING
        db.commit()

        # BERT logic
        class_result = classifier(email.body[:512])
        category = class_result[0]['label']

        # T5 logic
        summary_text = summarizer(email.body, max_length=45)[0]['summary_text']

        # BART logic
        result = zero_shot(email.body, candidate_labels=labels)
        if result['labels'][0] == "critical urgency":
            priority_score = result['scores'][0]
        elif result['labels'][0] == "moderate priority":
            priority_score = result['scores'][0] * 0.6
        else:
            priority_score = result['scores'][0] * 0.2

        new_analysis = Analysis(
            email_id=email.id,
            category=category,
            summary=summary_text,
            priority_score=round(priority_score, 2)
        )
        db.add(new_analysis)
        
        email.status = EmailStatus.COMPLETED
        db.commit()

    except Exception as e:
        db.rollback()
        if email:
            email.status = EmailStatus.FAILED
            db.commit()
        return f"Error: {str(e)}"
    finally:
        db.close()