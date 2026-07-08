"""Paper trader: the live bot loop, trading FAKE money against REAL prices.

Every CHECK_INTERVAL seconds it:
  1. downloads the latest candles,
  2. asks the strategy whether to buy, sell, or hold,
  3. executes the trade against an imaginary wallet,
  4. prints and logs what happened.

Nothing here can touch real money - there are no API keys and no order
calls. The wallet is saved to paper_wallet.json so the bot remembers its
position if you stop and restart it. Stop it any time with Ctrl+C.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from bot import dashboard, data, notifier, notion_logger, strategy

SYMBOL = "BTC/USDT"
TIMEFRAME = "4h"
CHECK_INTERVAL = 60  # seconds between checks
FEE_RATE = 0.001
# Must exceed the slow SMA window or the strategy can never compute it.
CANDLE_HISTORY = 250

WALLET_FILE = Path(__file__).resolve().parent.parent / "paper_wallet.json"
LOG_FILE = Path(__file__).resolve().parent.parent / "trades.log"


def load_wallet() -> dict:
    if WALLET_FILE.exists():
        return json.loads(WALLET_FILE.read_text())
    return {"cash": 1_000.0, "coins": 0.0}


def save_wallet(wallet: dict) -> None:
    WALLET_FILE.write_text(json.dumps(wallet, indent=2))


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{stamp}] {message}"
    print(line)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def check_once(wallet: dict) -> str:
    """One full decision cycle: fetch data, decide, trade. Returns the action."""
    candles = data.fetch_candles(SYMBOL, TIMEFRAME, limit=CANDLE_HISTORY)
    price = candles["close"].iloc[-1]
    holding = wallet["coins"] > 0

    action = strategy.latest_action(candles, currently_holding=holding)

    trade_size = 0.0
    pnl = None
    if action == "buy":
        wallet["last_buy_cost"] = wallet["cash"]
        wallet["coins"] = (wallet["cash"] * (1 - FEE_RATE)) / price
        trade_size = wallet["coins"]
        wallet["cash"] = 0.0
        save_wallet(wallet)
        log(f"BUY  {wallet['coins']:.6f} {SYMBOL.split('/')[0]} @ ${price:,.2f}")
    elif action == "sell":
        trade_size = wallet["coins"]
        wallet["cash"] = wallet["coins"] * price * (1 - FEE_RATE)
        pnl = wallet["cash"] - wallet.get("last_buy_cost", wallet["cash"])
        wallet["coins"] = 0.0
        save_wallet(wallet)
        log(f"SELL -> ${wallet['cash']:,.2f} @ ${price:,.2f}")
    else:
        total = wallet["cash"] + wallet["coins"] * price
        log(f"HOLD. Price ${price:,.2f}. Wallet worth ${total:,.2f}.")

    report(action, price, wallet, trade_size, pnl)
    return action


def report(action: str, price: float, wallet: dict,
           trade_size: float, pnl: float | None) -> None:
    """Best-effort reporting to dashboard/Notion/Telegram.

    Each channel fails independently and only logs a warning: a dead
    network or missing token must never stop the trading loop itself.
    """
    total = wallet["cash"] + wallet["coins"] * price
    holding = wallet["coins"] > 0

    channels = [
        ("dashboard", lambda: dashboard.record_run(action, price, total, holding)),
        ("notion run", lambda: notion_logger.log_run(action, price, total, holding)),
    ]
    if action in ("buy", "sell"):
        value = trade_size * price
        channels.append(("notion trade",
                         lambda: notion_logger.log_trade(action, price, trade_size, value, pnl)))
        channels.append(("telegram", lambda: notifier.notify_trade(action, price, total)))

    for name, send in channels:
        try:
            send()
        except Exception as exc:
            log(f"WARN: {name} reporting failed: {exc!r}")


def run_once() -> None:
    """Single check-and-exit, for running Koala on a schedule."""
    wallet = load_wallet()
    log(f"Koala single run. Wallet: ${wallet['cash']:,.2f} cash, "
        f"{wallet['coins']:.6f} coins. Watching {SYMBOL} ({TIMEFRAME}).")
    check_once(wallet)


def run() -> None:
    wallet = load_wallet()
    log(f"Paper trader started. Wallet: ${wallet['cash']:,.2f} cash, "
        f"{wallet['coins']:.6f} coins. Watching {SYMBOL} ({TIMEFRAME}).")

    while True:
        try:
            check_once(wallet)
        except Exception as exc:  # network blips etc. - log and keep running
            log(f"ERROR: {exc!r} - retrying next cycle")

        time.sleep(CHECK_INTERVAL)
