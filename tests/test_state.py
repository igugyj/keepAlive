"""测 trim_state 的裁剪逻辑，不碰网络。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from state import MAX_PROCESSED_UIDS, MAX_SENT_IDS, trim_state


def test_trim_keeps_only_tail():
    state = {
        "sent_message_ids": [f"<{i}@x>" for i in range(100)],
        "processed_uids": [str(i) for i in range(500)],
    }
    trim_state(state)
    assert len(state["sent_message_ids"]) == MAX_SENT_IDS
    assert state["sent_message_ids"][-1] == "<99@x>"
    assert state["sent_message_ids"][0] == f"<{100 - MAX_SENT_IDS}@x>"
    assert len(state["processed_uids"]) == MAX_PROCESSED_UIDS
    assert state["processed_uids"][-1] == "499"
    assert state["processed_uids"][0] == str(500 - MAX_PROCESSED_UIDS)


def test_trim_noop_when_under_limit():
    state = {
        "sent_message_ids": ["<a@x>", "<b@x>"],
        "processed_uids": ["1", "2"],
    }
    trim_state(state)
    assert state["sent_message_ids"] == ["<a@x>", "<b@x>"]
    assert state["processed_uids"] == ["1", "2"]


def test_trim_handles_missing_keys():
    state = {}
    trim_state(state)
    assert state == {}
