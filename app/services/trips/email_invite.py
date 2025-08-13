import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlencode
from typing import Optional
from app.core.config import settings

def generate_invite_link(invite_code: str) -> str:
    """
    Returns a frontend URL with invite code as query param
    """
    query = urlencode({"code": invite_code})
    return f"{settings.FRONTEND_BASE_URL}/accept-invite?{query}"

def send_invite_email(invitee_email: str, invite_link: str, trip_name: Optional[str] = None):
    """
    Sends invitation email to the provided user.
    """
    sender_email = settings.SMTP_USER
    subject = f"You're Invited to a Trip on TripMate 🎒"

    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = invitee_email
    message["Subject"] = subject

    html = f"""
    <html>
      <body>
        <p>Hey there,<br><br>
           You've been invited to join a trip on <strong>TripMate</strong>{f" - <b>{trip_name}</b>" if trip_name else ""}!<br><br>
           Click the button below to accept your invitation:<br><br>
           <a href="{invite_link}" style="padding: 10px 20px; background-color: #0984e3; color: white; text-decoration: none; border-radius: 5px;">Accept Invite</a>
           <br><br>
           Or paste this link into your browser:<br>
           <code>{invite_link}</code>
           <br><br>
           Happy planning! 🌍
        </p>
      </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)
    print(settings.SMTP_USER)

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            print(f"Using USER: {sender_email}")
            print(f"Using PASS: {settings.SMTP_PASSWORD}")
            

            server.login(sender_email, settings.SMTP_PASSWORD)
            server.sendmail(sender_email, invitee_email, message.as_string())
            print(f"[Email Invite] Sent to {invitee_email}")
    except Exception as e:
        print(f"[Email Invite] Failed to send to {invitee_email}: {e}")
