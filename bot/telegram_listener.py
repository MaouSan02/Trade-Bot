"""Telegram listener: reply with a status update when you message the bot.

Send "/update" or "update" to @koala_update_bot and Koala answers with
wallet, position, live BTC price, last run, and the test countdown.

This runs as a small always-on background process (started at logon by
the "Koala Telegram Listener" scheduled task). It long-polls Telegram's
getUpdates API - no server or public address needed - and only answers
messages coming from the chat ID in .env.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from bot import config, data
from bot.paper_trader import SYMBOL, load_wallet

LOG_FILE = config.PROJECT_DIR / "listener.log"
COMMANDS = ("/update", "update")


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with LOG_FILE.open("a") as f:
        f.write(f"[{stamp}] {message}\n")


def build_update() -> str:
    wallet = load_wallet()
    price = data.fetch_current_price(SYMBOL)
    total = wallet["cash"] + wallet["coins"] * price
    position = "Holding BTC" if wallet["coins"] > 0 else "In cash"

    last_line = ""
    data_file = config.PROJECT_DIR / "docs" / "data.json"
    if data_file.exists():
        history = json.loads(data_file.read_text())["history"]
        if history:
            last = history[-1]
            when = last["ts"][:16].replace("T", " ")  # trimmed to minutes
            last_line = f"Last run: {when} UTC — {last['action'].upper()}\n"

    return (
        f"🐨 Koala update\n"
        f"Wallet: ${total:,.2f} (paper) — {position}\n"
        f"BTC price: ${price:,.2f}\n"
        f"{last_line}"
        f"Test ends in {config.time_left_in_test()}"
    )


def run() -> None:
    env = config.load_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("Telegram not configured in .env - listener exiting.")
        return

    api = f"https://api.telegram.org/bot{token}"
    offset = 0
    log("Listener started.")
    while True:
        try:
            updates = requests.get(
                f"{api}/getUpdates",
                params={"offset": offset, "timeout": 50},
                timeout=60,
            ).json()
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                text = (message.get("text") or "").strip().lower()
                sender = str((message.get("chat") or {}).get("id"))
                if sender == str(chat_id) and text in COMMANDS:
                    requests.post(
                        f"{api}/sendMessage",
                        json={"chat_id": chat_id, "text": build_update()},
                        timeout=30,
                    )
                    log("Replied to update request.")
        except Exception as exc:  # network blip - wait and keep listening
            log(f"ERROR: {exc!r} - retrying in 15s")
            time.sleep(15)
