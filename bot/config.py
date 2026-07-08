"""Koala settings and secrets.

Secrets (API tokens) live in a .env file next to this project - a plain
text file of KEY=value lines that is .gitignore'd so it never reaches
GitHub. Anything missing from .env simply disables that feature.
"""

from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"

# The paper-trading evaluation window. When the countdown hits zero we
# review Koala's record and decide whether to move toward live trading.
TEST_START_UTC = "2026-07-08T13:00:00Z"
TEST_END_UTC = "2026-07-22T13:00:00Z"  # 14-day paper test

# Notion database IDs (the Koala HQ trackers).
NOTION_RUN_JOURNAL_DB = "15d828d4bfa5491c90f6f338494079dc"
NOTION_TRADE_LOG_DB = "bc7684f28dc5492fa10be91b76779532"


def load_env() -> dict:
    """Read KEY=value lines from .env. Returns {} if the file is absent."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def time_left_in_test() -> str:
    """Countdown to the end of the paper test, as 'dd:hh:mm:ss'."""
    end = datetime.fromisoformat(TEST_END_UTC.replace("Z", "+00:00"))
    remaining = end - datetime.now(timezone.utc)
    total = max(int(remaining.total_seconds()), 0)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}"
