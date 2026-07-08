"""Parameter sweep: backtest many strategy settings and compare them.

Tries each timeframe x SMA-window combination on the same coin and
prints a league table. Note: each test uses the last 1000 candles of its
timeframe, so longer timeframes cover a longer stretch of history
(1h ~ 41 days, 4h ~ 5.5 months, 1d ~ 2.7 years). That means rows are
only directly comparable within the same timeframe.

Run: python run_sweep.py
"""

from bot import backtest, data

SYMBOL = "BTC/USDT"
TIMEFRAMES = ["1h", "4h", "1d"]
SMA_WINDOWS = [(10, 30), (20, 50), (50, 200)]
CANDLES = 1000

results = []
for timeframe in TIMEFRAMES:
    print(f"Downloading {CANDLES} {timeframe} candles for {SYMBOL}...")
    df = data.fetch_candles(SYMBOL, timeframe, limit=CANDLES)
    period = f"{df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}"

    for fast, slow in SMA_WINDOWS:
        result = backtest.run(df, fast=fast, slow=slow)
        results.append({
            "timeframe": timeframe,
            "fast": fast,
            "slow": slow,
            "period": period,
            "return_pct": result.profit_pct,
            "buy_hold_pct": result.buy_hold_pct,
            "win_rate_pct": result.win_rate_pct,
            "max_dd_pct": result.max_drawdown_pct,
            "trades": len(result.trades),
            "round_trips": result.round_trips,
        })

print(f"\n=== Sweep results: {SYMBOL}, last {CANDLES} candles each ===")
header = (f"{'TF':>3} {'SMA':>7} {'Return':>8} {'B&H':>8} {'Edge':>8} "
          f"{'WinRate':>8} {'MaxDD':>7} {'Trades':>6}  Period")
print(header)
print("-" * len(header))
for r in sorted(results, key=lambda r: r["return_pct"] - r["buy_hold_pct"], reverse=True):
    edge = r["return_pct"] - r["buy_hold_pct"]  # how much we beat doing nothing by
    print(f"{r['timeframe']:>3} {r['fast']:>3}/{r['slow']:<3} "
          f"{r['return_pct']:>+7.2f}% {r['buy_hold_pct']:>+7.2f}% {edge:>+7.2f}% "
          f"{r['win_rate_pct']:>7.0f}% {r['max_dd_pct']:>6.2f}% {r['trades']:>6}  {r['period']}")
