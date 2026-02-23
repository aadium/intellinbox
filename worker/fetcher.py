from email.header import decode_header
import imaplib
import email
from backend.security import decrypt_password

def fetch_unseen_emails(inbox_model, limit=300):
    raw_password = decrypt_password(inbox_model.password)
    mail = imaplib.IMAP4_SSL(inbox_model.imap_server)
    
    try:
        mail.login(inbox_model.email_address, raw_password)
        mail.select("inbox")

        status, messages = mail.search(None, 'UNSEEN')
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
                        try:
                            body = part.get_payload(decode=True).decode(errors='replace')
                        except:
                            body = "[Could not decode body]"
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='replace')

            email_list.append({
                "sender": msg.get("From"),
                "subject": subject,
                "body": body,
                "message_id": message_id
            })

        return email_list

    finally:
        mail.logout()