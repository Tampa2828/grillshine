# email_utils.py
import os, smtplib, sys
from email.message import EmailMessage

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USERNAME or "no-reply@localhost")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

def _dev_print(subject, to, html_body, text_body):
    print("\n=== DEV EMAIL (no SMTP creds) ===", file=sys.stderr)
    print(f"TO: {to}", file=sys.stderr)
    print(f"SUBJECT: {subject}", file=sys.stderr)
    if text_body: print(f"\nTEXT:\n{text_body}", file=sys.stderr)
    print(f"\nHTML:\n{html_body}\n", file=sys.stderr)
    print("=== END DEV EMAIL ===\n", file=sys.stderr)

def send_email(subject, to, html_body, text_body=None, reply_to=None):
    if not (MAIL_USERNAME and MAIL_PASSWORD):
        _dev_print(subject, to, html_body, text_body); return
    msg = EmailMessage()
    msg["Subject"] = subject; msg["From"] = MAIL_FROM; msg["To"] = to
    if reply_to: msg["Reply-To"] = reply_to
    if text_body: msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    if MAIL_USE_TLS:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as s:
            s.starttls(); s.login(MAIL_USERNAME, MAIL_PASSWORD); s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT) as s:
            s.login(MAIL_USERNAME, MAIL_PASSWORD); s.send_message(msg)

def notify_admin(subject, html_body, text_body=None):
    if ADMIN_EMAIL:
        send_email(subject, ADMIN_EMAIL, html_body, text_body)
