"""The trading strategy: SMA crossover.

An SMA (Simple Moving Average) is just the average closing price over the
last N candles. It smooths out noise so you can see the trend.

The classic beginner strategy uses two of them:
  - a FAST average (e.g. last 10 candles) - reacts quickly to price moves
  - a SLOW average (e.g. last 30 candles) - shows the longer trend

Rules:
  BUY  when the fast average crosses ABOVE the slow one (uptrend starting)
  SELL when the fast average crosses BELOW the slow one (uptrend ending)

It is deliberately simple. It will NOT make you rich - its job is to give
the bot a clear, testable decision rule you can later replace.
"""

import pandas as pd

# Sweep winner 2026-07-08 (EXP-006 in the Koala Notion tracker):
# 50/200 on 4h candles was the only profitable config in the recent market.
FAST = 50
SLOW = 200


def add_indicators(df: pd.DataFrame, fast: int = FAST, slow: int = SLOW) -> pd.DataFrame:
    """Add the two moving-average columns to a candle DataFrame."""
    df = df.copy()
    df["sma_fast"] = df["close"].rolling(fast).mean()
    df["sma_slow"] = df["close"].rolling(slow).mean()
    return df


def add_signals(df: pd.DataFrame, fast: int = FAST, slow: int = SLOW) -> pd.DataFrame:
    """Add a `signal` column: 1 = be in the market, 0 = stay out.

    A "crossover" is the moment the signal flips, which is when we trade.
    """
    df = add_indicators(df, fast, slow)
    df["signal"] = (df["sma_fast"] > df["sma_slow"]).astype(int)
    # The first SLOW-1 rows have no slow average yet, so no signal.
    df.loc[df["sma_slow"].isna(), "signal"] = 0
    return df


def latest_action(df: pd.DataFrame, currently_holding: bool) -> str:
    """Decide what to do right now: 'buy', 'sell', or 'hold'.

    Used by the live paper trader. Looks only at the most recent
    *completed* candle so decisions don't flicker mid-candle.
    """
    df = add_signals(df)
    want_in = bool(df["signal"].iloc[-1])

    if want_in and not currently_holding:
        return "buy"
    if not want_in and currently_holding:
        return "sell"
    return "hold"
