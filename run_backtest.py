"""Test the strategy against recent history. Run: python run_backtest.py"""

from bot import backtest, data

SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
CANDLES = 1000  # ~41 days of hourly candles

print(f"Downloading the last {CANDLES} {TIMEFRAME} candles for {SYMBOL}...")
df = data.fetch_candles(SYMBOL, TIMEFRAME, limit=CANDLES)
print(f"Got data from {df.index[0]} to {df.index[-1]}.")

result = backtest.run(df)
backtest.print_report(result, SYMBOL, TIMEFRAME)
