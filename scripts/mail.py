import smtplib
from email.message import EmailMessage
import sys

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

USERNAME = "csutarmark@gmail.com    "
PASSWORD = open("/home/csuti/Development/mail/apppass", 'r').read().strip()

def notify(subject, text):
    msg = EmailMessage()
    msg["From"] = USERNAME
    msg["To"] = USERNAME
    msg["Subject"] = subject
    msg.set_content(text)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(USERNAME, PASSWORD)
        smtp.send_message(msg)

if len(sys.argv) < 2:
    print("Usage: python script.py 'mail body'")
    sys.exit(1)

param = sys.argv[1]

notify(
    "Sensor notification",
    param
)
