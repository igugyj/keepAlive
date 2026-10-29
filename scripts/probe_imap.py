"""临时探路：打印最近 5 封收件箱邮件的发件人和主题。"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# Windows 控制台默认 GBK，主题里的 emoji/Unicode 会炸，降级为替换字符
sys.stdout.reconfigure(errors="replace")

import email  # noqa: E402
import imaplib  # noqa: E402
from email.header import decode_header  # noqa: E402

from config import CONTROL_EMAIL, CONTROL_PASS, IMAP_HOST, IMAP_PORT  # noqa: E402

imaplib.Commands["ID"] = ("NONAUTH", "AUTH", "SELECTED")


def dec(raw):
    if not raw:
        return ""
    return "".join(
        t.decode(c or "utf-8", errors="replace") if isinstance(t, bytes) else t
        for t, c in decode_header(raw)
    )


imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
imap.login(CONTROL_EMAIL, CONTROL_PASS)
try:
    imap._simple_command("ID", '("name" "probe" "version" "0.1")')
    imap._untagged_response("OK", [None], "ID")
    imap.select("INBOX")
    typ, data = imap.search(None, "ALL")
    uids = data[0].split()[-5:] if data and data[0] else []
    for uid in uids:
        typ, msg_data = imap.fetch(uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        print("UID:", uid.decode())
        print("  From:", dec(msg.get("From")))
        print("  Subject:", dec(msg.get("Subject")))
        print("  Date:", msg.get("Date"))
finally:
    imap.logout()
