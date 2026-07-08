"""Maintain docs/data.json - the data feed behind the hosted dashboard.

The dashboard is a static page (docs/index.html) served by GitHub Pages.
It has no backend: it just fetches this JSON file, which Koala rewrites
on every run and the scheduled task pushes to GitHub.

History entry shape (one per cycle):
  {"ts": ..., "total": 998.10,
   "coins": {"BTC/USDT": {"price":..., "balance":..., "action":..., "holding":...}, ...}}
"""

import json
from datetime import datetime, timezone

from bot import config

DATA_FILE = config.PROJECT_DIR / "docs" / "data.json"
STARTING_BALANCE = 1_000.0


def _migrate(entry: dict) -> dict:
    """Convert a pre-multi-coin (BTC-only) history entry to the new shape."""
    if "coins" in entry:
        return entry
    return {
        "ts": entry["ts"],
        "total": entry["balance"],
        "coins": {"BTC/USDT": {"price": entry["price"], "balance": entry["balance"],
                               "action": entry["action"], "holding": entry["holding"]}},
    }


def _load() -> dict:
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text())
        data["history"] = [_migrate(e) for e in data.get("history", [])]
        return data
    return {"meta": {}, "history": [], "trades": []}


def record_cycle(results: dict, total: float) -> None:
    """Append this cycle's outcome for every coin and refresh metadata."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    data["meta"] = {
        "bot": "Koala",
        "symbols": config.SYMBOLS,
        "timeframe": "4h",
        "strategy": "SMA 50/200 crossover",
        "mode": "paper",
        "starting_balance": STARTING_BALANCE,
        "test_start": config.TEST_START_UTC,
        "test_end": config.TEST_END_UTC,
        "updated": now,
    }
    data["history"].append({
        "ts": now,
        "total": round(total, 2),
        "coins": {symbol: {
            "price": round(r["price"], 6),
            "balance": round(r["balance"], 2),
            "action": r["action"],
            "holding": r["holding"],
        } for symbol, r in results.items()},
    })
    for symbol, r in results.items():
        if r["action"] in ("buy", "sell"):
            data["trades"].append({"ts": now, "symbol": symbol, "side": r["action"],
                                   "price": round(r["price"], 6),
                                   "balance": round(r["balance"], 2)})

    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=1))
