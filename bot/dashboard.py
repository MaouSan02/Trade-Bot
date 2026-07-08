"""Maintain docs/data.json - the data feed behind the hosted dashboard.

The dashboard is a static page (docs/index.html) served by GitHub Pages.
It has no backend: it just fetches this JSON file, which Koala rewrites
on every run and the scheduled task pushes to GitHub.
"""

import json
from datetime import datetime, timezone

from bot import config

DATA_FILE = config.PROJECT_DIR / "docs" / "data.json"
STARTING_BALANCE = 1_000.0


def _load() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {"meta": {}, "history": [], "trades": []}


def record_run(action: str, price: float, balance: float, holding: bool) -> None:
    """Append this run's outcome and refresh the metadata block."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    data["meta"] = {
        "bot": "Koala",
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "strategy": "SMA 50/200 crossover (EXP-006)",
        "mode": "paper",
        "starting_balance": STARTING_BALANCE,
        "test_start": config.TEST_START_UTC,
        "test_end": config.TEST_END_UTC,
        "updated": now,
    }
    data["history"].append({
        "ts": now,
        "price": round(price, 2),
        "balance": round(balance, 2),
        "action": action,
        "holding": holding,
    })
    if action in ("buy", "sell"):
        data["trades"].append({"ts": now, "side": action, "price": round(price, 2),
                               "balance": round(balance, 2)})

    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=1))
