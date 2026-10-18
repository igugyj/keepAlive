"""测试前注入最小环境变量，避免 config 导入时抛错。"""

import os

os.environ.setdefault("CONTROL_EMAIL", "test@example.com")
os.environ.setdefault("CONTROL_PASS", "x")
os.environ.setdefault("WHITELIST_EMAILS", "a@example.com,b@example.com")
os.environ.setdefault("REMOTE_REPO", "owner/repo")
os.environ.setdefault("REMOTE_TOKEN", "x")
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("MAIL_DRY", "true")
