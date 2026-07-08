"""Auto-log Koala's runs and trades to the Notion trackers.

Uses Notion's REST API with an "internal integration" token. Setup:
  1. Create an integration at https://www.notion.so/profile/integrations
     (workspace: the one holding Koala HQ; capabilities: insert content).
  2. Put the token in .env as:  NOTION_TOKEN=ntn_xxx
  3. In Notion, open the Koala page -> ... menu -> Connections ->
     add your integration, so it may write to the databases.

If NOTION_TOKEN is missing, every function here is a silent no-op, so
the bot never breaks because logging is unconfigured.
"""

from datetime import datetime, timezone

import requests

from bot import config

API = "https://api.notion.com/v1/pages"
HEADERS_BASE = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def _token() -> str | None:
    return config.load_env().get("NOTION_TOKEN")


def _create_page(database_id: str, properties: dict) -> bool:
    token = _token()
    if not token:
        return False
    response = requests.post(
        API,
        headers={**HEADERS_BASE, "Authorization": f"Bearer {token}"},
        json={"parent": {"database_id": database_id}, "properties": properties},
        timeout=30,
    )
    response.raise_for_status()
    return True


def log_run(decision: str, price: float, balance: float, holding: bool,
            notes: str = "") -> bool:
    """Add a row to the Run Journal. Returns True if actually sent."""
    now = datetime.now(timezone.utc)
    return _create_page(config.NOTION_RUN_JOURNAL_DB, {
        "Run": {"title": [{"text": {"content": f"Auto run {now:%Y-%m-%d %H:%M} UTC"}}]},
        "Date": {"date": {"start": now.isoformat()}},
        "Decision": {"select": {"name": decision.capitalize()}},
        "BTC Price": {"number": round(price, 2)},
        "Balance": {"number": round(balance, 2)},
        "Holding?": {"checkbox": holding},
        "Notes": {"rich_text": [{"text": {"content": notes[:1900]}}]} if notes else {"rich_text": []},
    })


def log_trade(side: str, price: float, size: float, value: float,
              pnl: float | None = None) -> bool:
    """Add a row to the Trade Log. Returns True if actually sent."""
    now = datetime.now(timezone.utc)
    properties = {
        "Trade": {"title": [{"text": {"content": f"{side.upper()} BTC {now:%Y-%m-%d %H:%M} UTC"}}]},
        "Date": {"date": {"start": now.isoformat()}},
        "Side": {"select": {"name": side.capitalize()}},
        "Pair": {"select": {"name": "BTC/USDT"}},
        "Price": {"number": round(price, 2)},
        "Size": {"number": round(size, 8)},
        "Value": {"number": round(value, 2)},
        "Mode": {"select": {"name": "Paper"}},
        "Experiment": {"rich_text": [{"text": {"content": "EXP-006: SMA 50/200, BTC 4h"}}]},
    }
    if pnl is not None:
        properties["P&L"] = {"number": round(pnl, 2)}
    return _create_page(config.NOTION_TRADE_LOG_DB, properties)
