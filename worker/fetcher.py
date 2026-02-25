from email.header import decode_header
from email.utils import parsedate_to_datetime
import imaplib
import email

from bs4 import BeautifulSoup
from security import decrypt_password

def is_promotional(msg, body):
    sender = msg.get("From", "").lower()

    important_keywords = ["security", "alert", "verification", "invoice", "receipt", "order"]
    if "noreply" in sender and any(word in body.lower() for word in important_keywords):
        return False

    if msg.get("List-Unsubscribe"):
        return True

    promo_keywords = ["view in browser", "special offer", "discount", "opt out"]
    if any(word in body.lower()[:500] for word in promo_keywords):
        return True
            
    return False

def get_clean_text(html_body):
    if not html_body:
        return ""
    soup = BeautifulSoup(html_body, "html.parser")
    
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    return " ".join(soup.get_text(separator=" ").split())

def fetch_unseen_emails(inbox_model, condition):
    raw_password = decrypt_password(inbox_model.password)
    mail = imaplib.IMAP4_SSL(inbox_model.imap_server)
    
    try:
        mail.login(inbox_model.email_address, raw_password)
        mail.select("inbox")

        status, messages = mail.search(None, condition)
        if status != 'OK' or not messages[0]:
            return []

        all_ids = messages[0].split()
        recent_ids = all_ids
        
        email_list = []
        for num in recent_ids:
            status, data = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Duplicate checking
            message_id = msg.get("Message-ID")

            # Decode Subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            # Extract Body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors='replace')
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors='replace')

            # Only append if body has actual text content
            if body and body.strip():
                if not is_promotional(msg, body):
                    email_list.append({
                        "sender": msg.get("From"),
                        "received_at": parsedate_to_datetime(msg.get("Date")),
                        "subject": subject,
                        "body": body,
                        "message_id": message_id
                    })

        return email_list

    finally:
        mail.logout()