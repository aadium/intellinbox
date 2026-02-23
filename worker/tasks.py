import os
from celery import Celery
from celery.signals import worker_process_init
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Analysis, Email, EmailStatus, MonitoredInbox
from fetcher import fetch_unseen_emails
from transformers import pipeline

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

classifier = None
summarizer = None
zero_shot = None

@worker_process_init.connect
def init_worker(**kwargs):
    """Loads all three models once per worker process."""
    global classifier, summarizer, zero_shot
    print("--- Loading AI Models ---")
    
    # RoBERTa for 3-way Sentiment (Positive/Negative/Neutral)
    classifier = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")
    
    # T5 for Summarization
    summarizer = pipeline("summarization", model="t5-small")
    
    # BART for Zero-Shot Classification (Priority)
    zero_shot = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

@celery_app.task(name="tasks.analyze_email")
def analyze_email(email_id: int):
    global classifier, summarizer, zero_shot
    db = SessionLocal()

    if None in [classifier, summarizer, zero_shot]:
        init_worker()

    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email: return "Email not found"

        email.status = EmailStatus.PROCESSING
        db.commit()

        content = email.body[:1024]

        # Sentiment (RoBERTa)
        # Returns: 'positive', 'neutral', or 'negative'
        sent_result = classifier(content[:512])[0]
        category = sent_result['label'].lower()

        # B. Summary (T5)
        summary_text = summarizer(
            content, 
            max_length=90, 
            min_length=30, 
            do_sample=False,
            early_stopping=True
        )[0]['summary_text']
        
        summary_text = summary_text.strip().capitalize()
        if not summary_text.endswith('.'):
            summary_text += '...'

        # C. Priority (BART Zero-Shot)
        # Generic categories: Urgent, Neutral, Social
        labels = ["urgent action required", "neutral informational", "low priority social"]
        bart_result = zero_shot(content, candidate_labels=labels)
        top_label = bart_result['labels'][0]
        base_score = bart_result['scores'][0]

        # Generic Mapping Logic
        if "urgent" in top_label:
            priority_score = base_score
        elif "neutral" in top_label:
            priority_score = base_score * 0.5
        else:
            priority_score = base_score * 0.2

        # Final DB Save
        new_analysis = Analysis(
            email_id=email.id,
            category=category,
            summary=summary_text.strip(),
            priority_score=round(priority_score, 2)
        )
        db.add(new_analysis)
        
        email.status = EmailStatus.COMPLETED
        db.commit()
        return f"Done: {category} | {top_label}"

    except Exception as e:
        db.rollback()
        if email:
            email.status = EmailStatus.FAILED
            db.commit()
        return f"Error: {str(e)}"
    finally:
        db.close()

@celery_app.task(name="tasks.sync_inbox")
def sync_inbox_task(inbox_id: int):
    db = SessionLocal()
    try:
        # Get the inbox config
        inbox = db.query(MonitoredInbox).filter(MonitoredInbox.id == inbox_id).first()
        if not inbox or not inbox.is_active:
            return f"Inbox {inbox_id} not found or inactive."

        # Fetch recent 300 emails
        new_emails = fetch_unseen_emails(inbox, limit=300)
        
        added_count = 0
        for item in new_emails:
            # Deduplicate using Message-ID
            exists = db.query(Email).filter(
                Email.message_id == item['message_id']
            ).first()

            if not exists:
                db_email = Email(
                    sender=item['sender'],
                    subject=item['subject'],
                    body=item['body'],
                    message_id=item['message_id'],
                    inbox_id=inbox.id,
                    status=EmailStatus.PENDING
                )
                db.add(db_email)
                db.commit()
                db.refresh(db_email)

                celery_app.send_task("tasks.analyze_email", args=[db_email.id])
                added_count += 1
        
        return f"Successfully synced {inbox.email_address}. Added {added_count} new emails."
    
    finally:
        db.close()