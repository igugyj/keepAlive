"""总指挥：查 → 发 → 匹配 → 改仓库 → 存盘。"""

from __future__ import annotations

import logging
import sys
from datetime import timezone

from actions import write_remote
from checker import fetch_new_mails
from config import DRY_RUN, LOG_LEVEL, WHITELIST
from mailer import send_ping
from state import load_state, save_state, trim_state
from utils import (
    calc_silent_weeks,
    describe_active,
    is_whitelisted,
    mask_email,
    new_cycle_id,
    now_utc,
    parse_iso,
)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("main")

# ===== 区块：动态区模板 =====
CALLOUT_ALIVE = "> [!NOTE]\n> Active · {desc}"
CALLOUT_TIMEOUT = "> [!WARNING]\n> Inactive · {desc}\n> Last confirmed: {last_date}"
CALLOUT_TIMEOUT_NO_DATE = "> [!WARNING]\n> Inactive · {desc}"
DATE_FORMAT = "%Y-%m-%d"
# ===== 区块结束 =====


def build_block_text(status: str, desc: str, last_date: str | None = None) -> str:
    """只生成标记之间的 callout 内容，标记行本身不在这里。"""
    if status == "ALIVE":
        return CALLOUT_ALIVE.format(desc=desc)
    if last_date:
        return CALLOUT_TIMEOUT.format(desc=desc, last_date=last_date)
    return CALLOUT_TIMEOUT_NO_DATE.format(desc=desc)


def _format_last_date(iso: str | None) -> str | None:
    """把 last_alive_at 转成 YYYY-MM-DD，解析失败返回 None。"""
    dt = parse_iso(iso)
    return dt.strftime(DATE_FORMAT) if dt else None


def main() -> int:
    state = load_state()
    if not state.get("enabled", True):
        log.info("State disabled, skipping this run")
        return 0

    # ---- 1. 先查：取上一轮及更早到达的邮件 ----
    try:
        mails = fetch_new_mails(state.get("last_ping_at"))
    except Exception as e:
        log.error("Failed to fetch inbox: %s", e)
        return 1

    # ---- 2. 再发：本轮询问 ----
    cycle_id = new_cycle_id()
    try:
        sent_ids = send_ping(cycle_id)
    except Exception as e:
        log.error("Failed to send ping: %s", e)
        return 1
    state["sent_message_ids"].extend(sent_ids)
    state["last_ping_at"] = now_utc().isoformat()

    # ---- 3. 匹配：白名单 + 排除自己发的 + 未处理过 ----
    hit = None
    sent_set = set(state["sent_message_ids"])
    processed = set(state["processed_uids"])
    for m in mails:
        if not is_whitelisted(m["from"], WHITELIST):
            continue
        if m["message_id"] in sent_set:
            continue
        if m["uid"] in processed:
            continue
        hit = m
        break

    # ---- 4. 生成文本 & 改仓库 ----
    if hit:
        log.info(
            "Reply hit: uid=%s from=%s date=%s",
            hit["uid"],
            mask_email(hit["from"]),
            hit["date"].isoformat(),
        )
        # 统一存 UTC，避免邮件头的本地时区和 now_utc() 混用
        state["last_alive_at"] = hit["date"].astimezone(timezone.utc).isoformat()
        state["silent_weeks"] = 0
        state["processed_uids"].append(hit["uid"])
        block_text = build_block_text(status="ALIVE", desc=describe_active(0))
    else:
        weeks = calc_silent_weeks(state.get("last_alive_at"))
        state["silent_weeks"] = weeks
        last_date = _format_last_date(state.get("last_alive_at"))
        block_text = build_block_text(
            status="TIMEOUT", desc=describe_active(weeks), last_date=last_date
        )
        log.info("No reply hit, silent for %d week(s)", weeks)

    try:
        write_remote(block_text)
    except Exception as e:
        log.error("Failed to write target repo: %s", e)
        # 写仓库失败也把状态存下来，避免重复发信
        trim_state(state)
        save_state(state)
        return 1

    # ---- 5. 裁剪 & 存盘 ----
    trim_state(state)
    save_state(state)
    log.info("Done. DRY_RUN=%s", DRY_RUN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
