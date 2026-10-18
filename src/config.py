"""从环境变量读取配置。本地读 .env，Action 读 vars/secrets。"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# 本地存在 .env 就加载；Action 里没有此文件，静默跳过
load_dotenv()


def _env(key: str, default: str | None = None, required: bool = False) -> str:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing environment variable: {key}")
    return val  # type: ignore[return-value]


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    return int(raw) if raw else default


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ===== 区块：调试开关 =====
DRY_RUN: bool = _env_bool("DRY_RUN", False)
MAIL_DRY: bool = _env_bool("MAIL_DRY", False)
LOG_LEVEL: str = _env("LOG_LEVEL", "INFO")

# ===== 区块：控制邮箱 =====
CONTROL_EMAIL: str = _env("CONTROL_EMAIL", required=True)
CONTROL_PASS: str = _env("CONTROL_PASS", required=True)
IMAP_HOST: str = _env("IMAP_HOST", "imap.163.com")
IMAP_PORT: int = _env_int("IMAP_PORT", 993)
SMTP_HOST: str = _env("SMTP_HOST", "smtp.163.com")
SMTP_PORT: int = _env_int("SMTP_PORT", 465)

# ===== 区块：白名单 =====
WHITELIST: list[str] = [
    e.strip() for e in _env("WHITELIST_EMAILS", "").split(",") if e.strip()
]

# ===== 区块：目标仓库 =====
REMOTE_REPO: str = _env("REMOTE_REPO", required=True)
REMOTE_FILE: str = _env("REMOTE_FILE", "alive.txt")
REMOTE_BRANCH: str = _env("REMOTE_BRANCH", "main")
REMOTE_TOKEN: str = _env("REMOTE_TOKEN", required=True)

# ===== 区块：目标文件标记 =====
REMOTE_BLOCK_START: str = _env("REMOTE_BLOCK_START", "<!-- alive_start -->")
REMOTE_BLOCK_END: str = _env("REMOTE_BLOCK_END", "<!-- alive_end -->")

# ===== 区块：状态裁剪 =====
MAX_SENT_IDS: int = _env_int("MAX_SENT_IDS", 30)
MAX_PROCESSED_UIDS: int = _env_int("MAX_PROCESSED_UIDS", 100)

# ===== 区块：状态文件 =====
STATE_FILE: str = _env("STATE_FILE", "state.json")
