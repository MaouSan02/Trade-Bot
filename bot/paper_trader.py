"""Paper trader: the live bot loop, trading FAKE money against REAL prices.

Koala trades several coins at once. The $1,000 paper wallet is split into
equal "sleeves" - one per coin - and each sleeve runs the SMA strategy
independently: BTC can be holding while ETH sits in cash.

Every cycle, for each coin:
  1. download the latest candles,
  2. ask the strategy whether to buy, sell, or hold,
  3. execute against that coin's sleeve,
  4. report to the log, dashboard, Notion, and (for trades) Telegram.

Nothing here can touch real money - there are no API keys and no order
calls. The wallet is saved to paper_wallet.json so the bot remembers its
positions between runs.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from bot import config, dashboard, data, notifier, notion_logger, strategy

TIMEFRAME = "4h"
CHECK_INTERVAL = 60  # seconds between checks (loop mode)
FEE_RATE = 0.001
# Must exceed the slow SMA window or the strategy can never compute it.
CANDLE_HISTORY = 250
STARTING_CASH = 1_000.0

WALLET_FILE = Path(__file__).resolve().parent.parent / "paper_wallet.json"
LOG_FILE = Path(__file__).resolve().parent.parent / "trades.log"


def default_wallet() -> dict:
    share = round(STARTING_CASH / len(config.SYMBOLS), 2)
    return {symbol: {"cash": share, "coins": 0.0} for symbol in config.SYMBOLS}


def load_wallet() -> dict:
    if not WALLET_FILE.exists():
        return default_wallet()
    wallet = json.loads(WALLET_FILE.read_text())
    if "cash" in wallet:  # legacy single-coin format from before multi-coin
        return default_wallet()
    for symbol in config.SYMBOLS:  # a coin added later starts with no sleeve
        wallet.setdefault(symbol, {"cash": 0.0, "coins": 0.0})
    return wallet


def save_wallet(wallet: dict) -> None:
    WALLET_FILE.write_text(json.dumps(wallet, indent=2))


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{stamp}] {message}"
    print(line)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def check_symbol(symbol: str, sleeve: dict) -> dict:
    """One decision cycle for one coin's sleeve. Returns what happened."""
    candles = data.fetch_candles(symbol, TIMEFRAME, limit=CANDLE_HISTORY)
    # Cast out of numpy types - json (Notion, dashboard) can't serialize them.
    price = float(candles["close"].iloc[-1])
    holding = sleeve["coins"] > 0
    coin = symbol.split("/")[0]

    action = strategy.latest_action(candles, currently_holding=holding)

    trade_size = 0.0
    pnl = None
    if action == "buy":
        sleeve["last_buy_cost"] = sleeve["cash"]
        sleeve["coins"] = (sleeve["cash"] * (1 - FEE_RATE)) / price
        trade_size = sleeve["coins"]
        sleeve["cash"] = 0.0
        log(f"BUY  {trade_size:.6f} {coin} @ ${price:,.2f}")
    elif action == "sell":
        trade_size = sleeve["coins"]
        sleeve["cash"] = sleeve["coins"] * price * (1 - FEE_RATE)
        pnl = sleeve["cash"] - sleeve.get("last_buy_cost", sleeve["cash"])
        sleeve["coins"] = 0.0
        log(f"SELL {trade_size:.6f} {coin} -> ${sleeve['cash']:,.2f} @ ${price:,.2f}")
    else:
        value = sleeve["cash"] + sleeve["coins"] * price
        log(f"HOLD {coin}. Price ${price:,.2f}. Sleeve worth ${value:,.2f}.")

    return {
        "action": action,
        "price": price,
        "trade_size": trade_size,
        "pnl": pnl,
        "balance": float(sleeve["cash"] + sleeve["coins"] * price),
        "holding": bool(sleeve["coins"] > 0),
    }


def check_once(wallet: dict) -> dict:
    """Run one full cycle across every coin, then save and report."""
    results = {}
    for symbol in config.SYMBOLS:
        try:
            results[symbol] = check_symbol(symbol, wallet[symbol])
        except Exception as exc:  # one coin failing must not stop the others
            log(f"ERROR checking {symbol}: {exc!r}")
    save_wallet(wallet)
    report(results)
    return results


def report(results: dict) -> None:
    """Best-effort reporting to dashboard/Notion/Telegram.

    Each channel fails independently and only logs a warning: a dead
    network or missing token must never stop the trading loop itself.
    """
    total = sum(r["balance"] for r in results.values())
    channels = [("dashboard", lambda: dashboard.record_cycle(results, total))]

    for symbol, r in results.items():
        channels.append((f"notion run {symbol}",
                         lambda s=symbol, r=r: notion_logger.log_run(
                             s, r["action"], r["price"], total, r["holding"])))
        if r["action"] in ("buy", "sell"):
            channels.append((f"notion trade {symbol}",
                             lambda s=symbol, r=r: notion_logger.log_trade(
                                 s, r["action"], r["price"], r["trade_size"],
                                 r["trade_size"] * r["price"], r["pnl"])))
            channels.append((f"telegram {symbol}",
                             lambda s=symbol, r=r: notifier.notify_trade(
                                 r["action"], s, r["price"], total)))

    for name, send in channels:
        try:
            send()
        except Exception as exc:
            log(f"WARN: {name} reporting failed: {exc!r}")


def run_once() -> None:
    """Single check-and-exit, for running Koala on a schedule."""
    wallet = load_wallet()
    log(f"Koala single run. Watching {', '.join(config.SYMBOLS)} ({TIMEFRAME}).")
    check_once(wallet)


def run() -> None:
    wallet = load_wallet()
    log(f"Paper trader started. Watching {', '.join(config.SYMBOLS)} ({TIMEFRAME}).")
    while True:
        try:
            check_once(wallet)
        except Exception as exc:  # network blips etc. - log and keep running
            log(f"ERROR: {exc!r} - retrying next cycle")
        time.sleep(CHECK_INTERVAL)
