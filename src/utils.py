"""通用工具：时间、编号、文本描述。纯函数，先写先测。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional


def now_utc() -> datetime:
    """当前 UTC 时间（带时区）。"""
    return datetime.now(timezone.utc)


def parse_iso(s: Optional[str]) -> Optional[datetime]:
    """解析 ISO 时间字符串，统一返回带时区的 datetime。"""
    if not s:
        return None
    normalized = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def new_cycle_id() -> str:
    """生成本轮询问邮件的短编号，如 ALIVE-7F3A2C。"""
    return f"ALIVE-{uuid.uuid4().hex[:6].upper()}"


def calc_silent_weeks(last_alive_at_iso: Optional[str]) -> int:
    """计算距上次存活过了多少整周。未设置时返回 0。"""
    last = parse_iso(last_alive_at_iso)
    if last is None:
        return 0
    delta_days = (now_utc() - last).days
    return max(0, delta_days // 7)


def _plural(n: int, unit: str) -> str:
    """按数量返回单复数形式，如 '1 year' 或 '2 years'。"""
    suffix = "" if n == 1 else "s"
    return f"{n} {unit}{suffix}"


def describe_active(total_weeks: int) -> str:
    """按 52 周进年、4 周进月、余数为周的规则生成英文描述。"""
    if total_weeks <= 0:
        return "within 1 week"
    if total_weeks < 4:
        return f"{_plural(total_weeks, 'week')} ago"

    years = total_weeks // 52
    rem = total_weeks % 52
    months = rem // 4
    weeks = rem % 4

    parts = []
    if years:
        parts.append(_plural(years, "year"))
    if months:
        parts.append(_plural(months, "month"))
    if weeks:
        parts.append(_plural(weeks, "week"))
    if not parts:  # 兜底，理论上不会到
        parts.append(_plural(0, "week"))
    return " ".join(parts) + " ago"


def normalize_addr(raw: str) -> str:
    """从 'Name <a@b.com>' 提取 a@b.com 并转小写。"""
    if not raw:
        return ""
    if "<" in raw and ">" in raw:
        raw = raw[raw.index("<") + 1 : raw.index(">")]
    return raw.strip().lower()


def is_whitelisted(sender_raw: str, whitelist: list[str]) -> bool:
    """发件人是否在白名单内。"""
    addr = normalize_addr(sender_raw)
    return addr in {w.lower() for w in whitelist}


def mask_email(addr: str) -> str:
    """遮蔽邮箱本地部分，只保留首字符和域名，用于日志。"""
    if not addr or "@" not in addr:
        return "***"
    local, domain = addr.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"
