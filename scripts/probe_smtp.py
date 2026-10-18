"""临时探路：给白名单第一个地址发一封测试邮件。"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import smtplib  # noqa: E402
from email.message import EmailMessage  # noqa: E402
from email.utils import make_msgid  # noqa: E402

from config import (  # noqa: E402
    CONTROL_EMAIL,
    CONTROL_PASS,
    SMTP_HOST,
    SMTP_PORT,
    WHITELIST,
)

if not WHITELIST:
    print("Whitelist is empty, please configure WHITELIST_EMAILS")
    sys.exit(1)

msg = EmailMessage()
msg["From"] = CONTROL_EMAIL
msg["To"] = WHITELIST[0]
msg["Subject"] = "[PROBE] SMTP connectivity test"
msg["Message-ID"] = make_msgid(domain=CONTROL_EMAIL.split("@")[-1])
msg.set_content("If you see this, SMTP is working.")

with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
    smtp.login(CONTROL_EMAIL, CONTROL_PASS)
    smtp.send_message(msg)
print("Sent to", WHITELIST[0])
