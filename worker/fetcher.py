from email.header import decode_header
import imaplib
import email
from security import decrypt_password

def is_promotional(msg, body):
    if msg.get("List-Unsubscribe"):
        return True
    
    promo_keywords = ["unsubscribe", "view in browser", "privacy policy", "click here", "special offer"]
    body_lower = body.lower()
    if any(word in body_lower for word in promo_keywords):
        if len(body_lower) < 2000 and "opt out" in body_lower:
            return True
            
    return False

def fetch_unseen_emails(inbox_model, condition, limit=25):
    raw_password = decrypt_password(inbox_model.password)
    mail = imaplib.IMAP4_SSL(inbox_model.imap_server)
    
    try:
        mail.login(inbox_model.email_address, raw_password)
        mail.select("inbox")

        status, messages = mail.search(None, condition)
        if status != 'OK' or not messages[0]:
            return []

        all_ids = messages[0].split()
        recent_ids = all_ids[-limit:]
        
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
                        "subject": subject,
                        "body": body.strip(),
                        "message_id": message_id
                    })

        return email_list

    finally:
        mail.logout()