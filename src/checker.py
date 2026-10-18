"""IMAP 查控制邮箱收件箱。只负责取回邮件，不做业务判断。"""

from __future__ import annotations

import email
import imaplib
import logging
from datetime import timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr

from config import CONTROL_EMAIL, CONTROL_PASS, IMAP_HOST, IMAP_PORT
from utils import now_utc, parse_iso

log = logging.getLogger(__name__)

# 部分邮箱（如 163）要求客户端先发 ID 声明，否则 FETCH 会被拒绝
imaplib.Commands["ID"] = ("NONAUTH", "AUTH", "SELECTED")


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    out = []
    for text, charset in decode_header(raw):
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _send_id(imap: imaplib.IMAP4_SSL) -> None:
    """发送 IMAP ID。name/vendor 为协议字段，保持英文以兼容服务器。"""
    try:
        args = '("name" "alive-bot" "version" "1.0.0" "vendor" "python")'
        imap._simple_command("ID", args)
        imap._untagged_response("OK", [None], "ID")
    except Exception as e:  # ID 失败不阻断主流程
        log.debug("Failed to send IMAP ID (ignorable): %s", e)


def fetch_new_mails(last_ping_at_iso: str | None) -> list[dict]:
    """返回 last_ping_at 之后到达的收件箱邮件列表。"""
    since_dt = parse_iso(last_ping_at_iso)
    if since_dt is None:
        since_dt = now_utc() - timedelta(days=7)
    # IMAP SINCE 只精确到天，往前多取一天，Python 里再精筛
    since_str = (since_dt - timedelta(days=1)).strftime("%d-%b-%Y")

    results: list[dict] = []
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        imap.login(CONTROL_EMAIL, CONTROL_PASS)
        _send_id(imap)
        imap.select("INBOX")
        typ, data = imap.search(None, f'(SINCE "{since_str}")')
        if typ != "OK":
            log.warning("IMAP search returned non-OK status: %s", typ)
            return results

        uid_list = data[0].split() if data and data[0] else []
        if not uid_list:
            return results

        for uid in uid_list:
            uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
            typ, msg_data = imap.fetch(uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            msg_id = (msg.get("Message-ID") or "").strip()
            from_raw = _decode_header(msg.get("From"))
            from_addr = parseaddr(from_raw)[1].lower()

            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=now_utc().tzinfo)
            except Exception:
                dt = now_utc()

            # 精筛：只保留晚于 last_ping_at 的邮件
            if dt <= since_dt:
                continue

            results.append(
                {
                    "uid": uid_str,
                    "from": from_addr,
                    "message_id": msg_id,
                    "date": dt,
                }
            )
        log.info("Fetched %d candidate mail(s) from control inbox", len(results))
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return results
