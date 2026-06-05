"""Entrega redundante: SMTP e Telegram."""
import logging
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx

from app import config

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_email(subject: str, body: str, attachment: Path | None = None) -> bool:
    msg = MIMEMultipart()
    msg["From"]    = config.EMAIL_FROM
    msg["To"]      = ", ".join(config.EMAIL_TO)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment and attachment.exists():
        with open(attachment, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={attachment.name}")
        msg.attach(part)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())
        logger.info("Email enviado para %s", ", ".join(config.EMAIL_TO))
        return True
    except Exception:
        logger.exception("Falha ao enviar email")
        return False


def send_telegram(message: str, document: Path | None = None) -> bool:
    try:
        if document and document.exists():
            with open(document, "rb") as f:
                resp = httpx.post(
                    f"{TELEGRAM_API}/sendDocument",
                    data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": message},
                    files={"document": (document.name, f)},
                    timeout=30,
                )
        else:
            resp = httpx.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": config.TELEGRAM_CHAT_ID, "text": message},
                timeout=30,
            )
        resp.raise_for_status()
        logger.info("Telegram enviado")
        return True
    except Exception:
        logger.exception("Falha ao enviar Telegram")
        return False


def deliver(subject: str, body: str, attachment: Path | None = None) -> dict[str, bool]:
    return {
        "email":    send_email(subject, body, attachment),
        "telegram": send_telegram(body, attachment),
    }
