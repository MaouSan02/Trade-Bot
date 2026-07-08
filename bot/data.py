"""Fetch market data from a crypto exchange.

Exchanges publish price history as OHLCV "candles": for each time slice
(e.g. one hour) you get the Open, High, Low, Close price and Volume traded.
This is public data - no account or API key required.
"""

import ccxt
import pandas as pd


def get_exchange() -> ccxt.Exchange:
    """Connect to Binance's public API (read-only, no keys)."""
    return ccxt.binance()


def fetch_candles(symbol: str = "BTC/USDT", timeframe: str = "1h",
                  limit: int = 500) -> pd.DataFrame:
    """Fetch the most recent `limit` candles for a trading pair.

    symbol    - what to trade, e.g. "BTC/USDT" (Bitcoin priced in dollars)
    timeframe - candle size: "1m", "5m", "1h", "4h", "1d", ...
    limit     - how many candles (Binance caps a single request at 1000)
    """
    exchange = get_exchange()
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    # Exchange timestamps are milliseconds since 1970; make them readable dates.
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    return df


def fetch_current_price(symbol: str = "BTC/USDT") -> float:
    """Get the latest traded price for a pair."""
    exchange = get_exchange()
    ticker = exchange.fetch_ticker(symbol)
    return ticker["last"]
