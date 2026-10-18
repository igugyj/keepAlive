"""把 callout 写进目标文件的标记区块内。用 GitHub Contents API。"""

from __future__ import annotations

import base64
import logging
import re

import requests

from config import (
    DRY_RUN,
    REMOTE_BLOCK_END,
    REMOTE_BLOCK_START,
    REMOTE_BRANCH,
    REMOTE_FILE,
    REMOTE_REPO,
    REMOTE_TOKEN,
)

log = logging.getLogger(__name__)

API_BASE = "https://api.github.com"

# ===== 区块：提交信息 =====
COMMIT_MESSAGE_TEMPLATE = "keep-alive update: {file}"
LOG_DRY_WRITE = "[DRY-RUN] Would update block in %s/%s (%s):\n%s"
LOG_WRITTEN = "Updated block in %s/%s"
# ===== 区块结束 =====


def _api_url() -> str:
    return f"{API_BASE}/repos/{REMOTE_REPO}/contents/{REMOTE_FILE}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {REMOTE_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_current() -> tuple[str, str | None]:
    """取目标文件当前内容和解码后的 sha。文件不存在时返回 ("", None)。"""
    r = requests.get(
        _api_url(), headers=_headers(), params={"ref": REMOTE_BRANCH}, timeout=15
    )
    if r.status_code == 404:
        return "", None
    if r.status_code != 200:
        log.error("Failed to read target file, status %s: %s", r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def _replace_block(original: str, new_inner: str) -> str:
    """保留标记行，只替换两个标记之间的内容。"""
    start = REMOTE_BLOCK_START
    end = REMOTE_BLOCK_END

    if original.count(start) != 1 or original.count(end) != 1:
        raise RuntimeError(
            f"Marker must appear exactly once: start={original.count(start)}, "
            f"end={original.count(end)}"
        )
    if original.index(start) > original.index(end):
        raise RuntimeError("Marker order is wrong: end appears before start")

    # 用正则非贪婪匹配，保留标记行本身
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    replacement = f"{start}\n{new_inner.strip()}\n{end}"
    return pattern.sub(lambda _: replacement, original, count=1)


def write_remote(block_text: str) -> None:
    """把 block_text 写进目标文件的标记区块内。DRY_RUN 时只打印。"""
    if DRY_RUN:
        log.info(LOG_DRY_WRITE, REMOTE_REPO, REMOTE_FILE, REMOTE_BRANCH, block_text)
        return

    original, sha = _get_current()
    if not original:
        raise RuntimeError(
            f"Target file not found or empty: {REMOTE_REPO}/{REMOTE_FILE}"
        )

    new_content = _replace_block(original, block_text)
    if new_content == original:
        log.info("Block content unchanged, skip write")
        return

    body = {
        "message": COMMIT_MESSAGE_TEMPLATE.format(file=REMOTE_FILE),
        "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
        "branch": REMOTE_BRANCH,
    }
    if sha:
        body["sha"] = sha

    r = requests.put(_api_url(), headers=_headers(), json=body, timeout=15)
    if r.status_code not in (200, 201):
        log.error("Failed to write target repo, status %s: %s", r.status_code, r.text)
        r.raise_for_status()
    log.info(LOG_WRITTEN, REMOTE_REPO, REMOTE_FILE)
