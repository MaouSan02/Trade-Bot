"""Telegram push notifications for Koala's trades.

Setup (five minutes, once):
  1. In Telegram, message @BotFather -> /newbot -> pick a name
     (e.g. "Koala Trade Bot") -> BotFather replies with a token.
  2. Message your new bot anything (this opens the chat).
  3. Visit https://api.telegram.org/bot<TOKEN>/getUpdates in a browser
     and copy the "chat" -> "id" number from the reply.
  4. Add both to .env:
        TELEGRAM_BOT_TOKEN=123456:ABC-xyz
        TELEGRAM_CHAT_ID=123456789

If either value is missing, sending is a silent no-op - the bot never
fails because notifications are unconfigured.
"""

import requests

from bot import config


def send(message: str) -> bool:
    """Send a Telegram message. Returns True if actually sent."""
    env = config.load_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=30,
    )
    response.raise_for_status()
    return True


def notify_trade(side: str, symbol: str, price: float, wallet_value: float) -> bool:
    """Push a trade alert including the paper-test countdown."""
    emoji = "🟢" if side == "buy" else "🔴"
    coin = symbol.split("/")[0]
    return send(
        f"{emoji} Koala {side.upper()} {coin} @ ${price:,.4f}\n"
        f"Total wallet: ${wallet_value:,.2f} (paper)\n"
        f"Test ends in {config.time_left_in_test()}"
    )
