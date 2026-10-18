"""state.json 的读写。只存记忆，不存配置。"""

from __future__ import annotations

import json
import os

from config import MAX_PROCESSED_UIDS, MAX_SENT_IDS, STATE_FILE
from utils import now_utc


def _initial_state() -> dict:
    ts = now_utc().isoformat()
    return {
        "last_alive_at": ts,
        "last_ping_at": ts,
        "silent_weeks": 0,
        "sent_message_ids": [],
        "processed_uids": [],
        "enabled": True,
    }


def trim_state(state: dict) -> None:
    """保留最近若干条记录，防止 state.json 无限增长。"""
    if len(state.get("sent_message_ids", [])) > MAX_SENT_IDS:
        state["sent_message_ids"] = state["sent_message_ids"][-MAX_SENT_IDS:]
    if len(state.get("processed_uids", [])) > MAX_PROCESSED_UIDS:
        state["processed_uids"] = state["processed_uids"][-MAX_PROCESSED_UIDS:]


def load_state(path: str = STATE_FILE) -> dict:
    if not os.path.exists(path):
        state = _initial_state()
        save_state(state, path)
        return state
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse state file: {e}") from e
    # 补全缺失字段，兼容老版本
    for k, v in _initial_state().items():
        state.setdefault(k, v)
    return state


def save_state(state: dict, path: str = STATE_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
