import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from app.core.config import settings

SENDER_NAME = settings.APP_NAME
SENDER_EMAIL = settings.SMTP_USER

def send_email_text(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
    msg["To"] = to_email

    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())