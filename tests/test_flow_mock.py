"""用 mock 测 main 的编排分支，不碰网络和仓库。"""

import os
import sys
from datetime import datetime, timezone

# 必须在 import main 之前设置，否则 config.py 顶层会因缺少环境变量抛错
os.environ.setdefault("CONTROL_EMAIL", "test@example.com")
os.environ.setdefault("CONTROL_PASS", "x")
os.environ.setdefault("WHITELIST_EMAILS", "a@example.com,b@example.com")
os.environ.setdefault("REMOTE_REPO", "owner/repo")
os.environ.setdefault("REMOTE_TOKEN", "x")
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("MAIL_DRY", "true")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import main as main_mod
from state import save_state


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """每个用例用独立 state 文件，并 patch 掉各外部依赖。"""
    state_path = str(tmp_path / "state.json")
    monkeypatch.setattr("state.STATE_FILE", state_path)
    monkeypatch.setattr(main_mod, "load_state", lambda: _load(state_path))
    monkeypatch.setattr(main_mod, "save_state", lambda s: save_state(s, state_path))
    return state_path


def _load(path):
    from state import load_state

    return load_state(path)


def _mail(uid, sender, msg_id, dt):
    return {"uid": uid, "from": sender, "message_id": msg_id, "date": dt}


def test_hit_updates_silent_to_zero(tmp_state, monkeypatch):
    save_state(
        {
            "last_alive_at": "2026-10-01T00:00:00+00:00",
            "last_ping_at": "2026-10-10T00:00:00+00:00",
            "silent_weeks": 3,
            "sent_message_ids": [],
            "processed_uids": [],
            "enabled": True,
        },
        tmp_state,
    )

    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    reply = _mail("uid1", "a@example.com", "<reply@x>", now)
    monkeypatch.setattr(main_mod, "fetch_new_mails", lambda _: [reply])
    monkeypatch.setattr(main_mod, "send_ping", lambda cid: ["<ping@x>"])
    captured = {}
    monkeypatch.setattr(
        main_mod, "write_remote", lambda t: captured.setdefault("text", t)
    )
    monkeypatch.setattr(main_mod, "now_utc", lambda: now)

    assert main_mod.main() == 0
    assert "within 1 week" in captured["text"]
    state = _load(tmp_state)
    assert state["silent_weeks"] == 0
    assert state["last_alive_at"].startswith("2026-10-18")
    assert "uid1" in state["processed_uids"]


def test_no_hit_increases_silent(tmp_state, monkeypatch):
    save_state(
        {
            "last_alive_at": "2026-10-01T00:00:00+00:00",
            "last_ping_at": "2026-10-10T00:00:00+00:00",
            "silent_weeks": 0,
            "sent_message_ids": [],
            "processed_uids": [],
            "enabled": True,
        },
        tmp_state,
    )

    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    # 发件人不在白名单，应被忽略
    other = _mail("uid9", "stranger@evil.com", "<x@y>", now)
    monkeypatch.setattr(main_mod, "fetch_new_mails", lambda _: [other])
    monkeypatch.setattr(main_mod, "send_ping", lambda cid: ["<ping@x>"])
    captured = {}
    monkeypatch.setattr(
        main_mod, "write_remote", lambda t: captured.setdefault("text", t)
    )
    monkeypatch.setattr(main_mod, "now_utc", lambda: now)

    assert main_mod.main() == 0
    assert "week" in captured["text"] or "month" in captured["text"]
    state = _load(tmp_state)
    assert state["silent_weeks"] >= 2


def test_disabled_exits_early(tmp_state, monkeypatch):
    save_state(
        {
            "last_alive_at": "2026-10-01T00:00:00+00:00",
            "last_ping_at": "2026-10-10T00:00:00+00:00",
            "silent_weeks": 0,
            "sent_message_ids": [],
            "processed_uids": [],
            "enabled": False,
        },
        tmp_state,
    )

    called = {"fetch": False, "send": False}
    monkeypatch.setattr(
        main_mod, "fetch_new_mails", lambda _: called.update(fetch=True)
    )
    monkeypatch.setattr(main_mod, "send_ping", lambda cid: called.update(send=True))

    assert main_mod.main() == 0
    assert called == {"fetch": False, "send": False}
