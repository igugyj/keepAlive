# AGENTS.md

Mail-based keep-alive bot: GitHub Actions periodically emails a whitelist, matches replies via IMAP, and rewrites a status callout in a remote repo file. Config in Chinese; see `README.md` for full behavior docs (generally accurate except where noted below).

## Commands

```bash
uv sync                              # install deps (Python 3.13 pinned via .python-version)
uv run pytest tests/ -v              # all tests
uv run pytest tests/test_flow_mock.py::test_hit_updates_silent_to_zero  # single test
uv run python scripts/run_local.py   # local run (uses .env; supports DRY_RUN/MAIL_DRY)
uv run python scripts/probe_imap.py  # connectivity check before real runs
uv run python scripts/probe_smtp.py
```

No linter, formatter, or typecheck is configured. The only dev dependency is pytest.

## Architecture gotchas

- `src/` is **not** a package: no `__init__.py`, modules import each other flat (`from config import ...`). This works because entrypoints put `src/` on `sys.path`:
  - CI: `uv run python src/main.py` (script dir is auto-added)
  - Local: `scripts/run_local.py` inserts `src/` manually
  - Tests: each test module that imports `main` does its own `sys.path.insert` — do the same in new test files.
- `src/config.py` reads required env vars **at import time** and raises `RuntimeError` if missing. `tests/conftest.py` injects dummies via `os.environ.setdefault` — any new test importing `src` modules needs env vars set *before* the import.
- SMTP/IMAP both log in with `CONTROL_EMAIL`/`CONTROL_PASS` — single Gmail account only; app password required (login password is rejected with 535). Gmail IMAP must be enabled in web settings (off by default). Other providers are out of scope by design — Outlook.com personal accounts are unusable here (basic auth permanently disabled, OAuth2 not implemented).
- `mailer._open_smtp()`: port 465 → `SMTP_SSL` (Gmail default), any other port → `SMTP` + `starttls()`. The `From` header is `CONTROL_EMAIL` so replies land in the control inbox.
- Flow in `src/main.py`: fetch inbox first, then send pings (so this cycle's pings never match this cycle's replies). Matching requires: sender in whitelist + Message-ID not in `sent_message_ids` + UID not in `processed_uids`.
- `state.json` is committed state, not config. **It is tracked in git and the workflow commits/pushes updates to it** — preserve its schema (`last_alive_at`, `last_ping_at`, `silent_weeks`, `sent_message_ids`, `processed_uids`, `enabled`). A missing file self-initializes on load.
- `src/actions.py` only rewrites the region between `REMOTE_BLOCK_START`/`REMOTE_BLOCK_END` (default `<!-- alive_start -->` / `<!-- alive_end -->`); markers must appear exactly once each and in order, else it errors without writing.

## Discrepancies / cautions

- `README.md` says cron is Monday 08:00 UTC; the actual schedule in `.github/workflows/alive.yml` is `32 10 * * 3` (Wednesday 10:32 UTC). Trust the workflow.
- `.env` (gitignored, may contain real credentials) is loaded automatically by `src/config.py` via `python-dotenv`. Never commit it or log unmasked emails — logs deliberately mask addresses (`mask_email`).
- CI runs with `DRY_RUN`/`MAIL_DRY` hardcoded to `"false"`; use those flags for safe local runs.
- Workflow deploys nothing; it just runs `main.py` and commits `state.json` (`permissions: contents: write`).
