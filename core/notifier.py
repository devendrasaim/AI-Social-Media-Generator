import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import (
    DISCORD_WEBHOOK_URL, 
    SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, 
    NOTIFICATION_EMAIL
)

logger = logging.getLogger(__name__)

def send_discord_alert(message):
    """Send a message to a Discord channel via Webhook."""
    if not DISCORD_WEBHOOK_URL:
        return

    try:
        payload = {"content": f"📢 **Automation Alert**\n{message}"}
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        logger.info("Discord alert sent.")
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")

def send_email_alert(subject, body):
    """Send an email alert via SMTP."""
    if not all([SMTP_USER, SMTP_PASSWORD, NOTIFICATION_EMAIL]):
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFICATION_EMAIL
        msg["Subject"] = f"AI Generator Alert: {subject}"
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info("Email alert sent.")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

def notify_all(subject, message):
    """Send alert to both Discord and Email if configured."""
    logger.info(f"Notification: {subject} - {message}")
    send_discord_alert(f"**{subject}**\n{message}")
    send_email_alert(subject, message)
