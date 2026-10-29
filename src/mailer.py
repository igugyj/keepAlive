"""SMTP 发询问邮件。每封 Message-ID 自己生成，便于精确排除。"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from config import (
    CONTROL_EMAIL,
    CONTROL_PASS,
    MAIL_DRY,
    SMTP_HOST,
    SMTP_PORT,
    WHITELIST,
)
from utils import mask_email

log = logging.getLogger(__name__)

# ===== 区块：邮件资源 =====
SENDER_NAME = "alive-bot"
SUBJECT_TEMPLATE = "[{cycle_id}] Please reply with any content to confirm keep-alive"
BODY_TEXT = "Just reply to this email with any content."
LOG_DRY = "[MAIL-DRY] Would send to %s"
LOG_SENT = "Sent ping to %s"
# ===== 区块结束 =====


def _open_smtp():
    """465 用隐式 TLS（Gmail smtp.gmail.com），587 用 STARTTLS。"""
    if SMTP_PORT == 465:
        return smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    smtp.starttls()
    return smtp


def send_ping(cycle_id: str) -> list[str]:
    """向白名单每个地址各发一封询问邮件，返回发出的 Message-ID 列表。"""
    subject = SUBJECT_TEMPLATE.format(cycle_id=cycle_id)
    body = BODY_TEXT

    domain = CONTROL_EMAIL.split("@")[-1] if "@" in CONTROL_EMAIL else "alive.local"
    sent_ids: list[str] = []

    for recipient in WHITELIST:
        msg = EmailMessage()
        msg["From"] = formataddr((SENDER_NAME, CONTROL_EMAIL))
        msg["To"] = recipient
        msg["Subject"] = subject
        # 自己生成并写入 Message-ID，才能拿回来做排除
        msg_id = make_msgid(domain=domain)
        msg["Message-ID"] = msg_id
        msg.set_content(body)

        if MAIL_DRY:
            log.info(LOG_DRY, mask_email(recipient))
            sent_ids.append(msg_id)
            continue

        with _open_smtp() as smtp:
            smtp.login(CONTROL_EMAIL, CONTROL_PASS)
            smtp.send_message(msg)
        log.info(LOG_SENT, mask_email(recipient))
        sent_ids.append(msg_id)

    return sent_ids
