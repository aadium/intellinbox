import datetime
import os
from celery import Celery
from celery.signals import worker_process_init
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Analysis, Email, EmailStatus, MonitoredInbox
from fetcher import fetch_unseen_emails, get_clean_text
from transformers import pipeline
from bs4 import BeautifulSoup

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
    email = None # Initialize for the finally block

    try:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email: 
            return "Email not found"

        email.status = EmailStatus.PROCESSING
        db.commit()

        if not email.body or not email.body.strip():
            raise ValueError("Email body is empty; cannot analyze.")
        
        clean_content = get_clean_text(email.body)
        content = clean_content[:1024]

        sent_result = classifier(content[:512])[0]
        category = sent_result['label'].lower()

        summary_results = summarizer(
            content, 
            max_length=90, 
            min_length=30, 
            do_sample=False
        )
        summary_text = summary_results[0]['summary_text'].strip().capitalize()
        if not summary_text.endswith('.'): summary_text += '...'

        labels = ["urgent action required", "neutral informational", "low priority social"]
        bart_result = zero_shot(content, candidate_labels=labels)

        top_label = bart_result['labels'][0]
        base_score = bart_result['scores'][0]
        priority_score = base_score * (1.0 if "urgent" in top_label else 0.5 if "neutral" in top_label else 0.2)

        new_analysis = Analysis(
            email_id=email.id,
            category=category,
            summary=summary_text,
            priority_score=round(priority_score, 2)
        )
        db.add(new_analysis)

        email.status = EmailStatus.COMPLETED
        db.commit()
        return f"Success: {category}"

    except Exception as e:
        print(f"TASK ERROR for Email {email_id}: {str(e)}")
        db.rollback()

        if email:
            db.query(Email).filter(Email.id == email_id).update({"status": EmailStatus.FAILED})
            db.commit()
        return f"Failed: {str(e)}"
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

        # Fetch recent emails
        new_emails = fetch_unseen_emails(inbox, '(UNSEEN NOT FROM "noreply@")')
        
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
        
        inbox.last_synced = func.now()
        db.commit()
        return f"Successfully synced {inbox.email_address}. Added {added_count} new emails."
    
    finally:
        db.close()

@celery_app.task(name="tasks.setup_inbox")
def setup_inbox_task(inbox_id: int):
    db = SessionLocal()
    try:
        # Get the inbox config
        inbox = db.query(MonitoredInbox).filter(MonitoredInbox.id == inbox_id).first()
        if not inbox or not inbox.is_active:
            return f"Inbox {inbox_id} not found or inactive."

        # Fetch recent emails
        import datetime
        date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%d-%b-%Y")
        new_emails = fetch_unseen_emails(inbox, f'SINCE "{date}" NOT FROM "noreply@"')
        
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
        
        inbox.last_synced = func.now()
        db.commit()
        return f"Successfully synced {inbox.email_address}. Added {added_count} new emails."
    
    finally:
        db.close()