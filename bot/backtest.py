"""Backtester: replay the strategy over historical candles.

We walk through history one candle at a time, pretending to trade with
$1,000. When the strategy says buy, we spend all our cash on coin; when
it says sell, we convert it all back to cash. Every trade pays the
exchange fee (0.1% on Binance), because fees quietly kill many
strategies that look good on paper.

At the end we compare against "buy and hold" - just buying on day one
and doing nothing. If the strategy can't beat that, the strategy isn't
adding anything.
"""

from dataclasses import dataclass, field

import pandas as pd

from bot import strategy

STARTING_CASH = 1_000.0
FEE_RATE = 0.001  # 0.1% per trade, Binance's standard taker fee


@dataclass
class Result:
    trades: list = field(default_factory=list)
    final_value: float = 0.0
    buy_hold_value: float = 0.0
    max_drawdown_pct: float = 0.0  # worst peak-to-trough fall in wallet value
    wins: int = 0                  # round trips that made money after fees
    round_trips: int = 0           # completed buy->sell pairs

    @property
    def profit_pct(self) -> float:
        return (self.final_value / STARTING_CASH - 1) * 100

    @property
    def buy_hold_pct(self) -> float:
        return (self.buy_hold_value / STARTING_CASH - 1) * 100

    @property
    def win_rate_pct(self) -> float:
        return (self.wins / self.round_trips * 100) if self.round_trips else 0.0


def run(df: pd.DataFrame, fast: int = strategy.FAST, slow: int = strategy.SLOW) -> Result:
    """Simulate trading the strategy over the given candle history."""
    df = strategy.add_signals(df, fast, slow)

    cash = STARTING_CASH
    coins = 0.0
    result = Result()

    prev_signal = 0
    last_buy_cost = 0.0  # cash spent on the open position, to score the round trip
    peak = STARTING_CASH
    for timestamp, row in df.iterrows():
        signal = row["signal"]
        price = row["close"]

        if signal == 1 and prev_signal == 0 and cash > 0:
            # Crossover up -> buy with everything we have, minus the fee.
            last_buy_cost = cash
            coins = (cash * (1 - FEE_RATE)) / price
            result.trades.append(("BUY", timestamp, price))
            cash = 0.0
        elif signal == 0 and prev_signal == 1 and coins > 0:
            # Crossover down -> sell everything, minus the fee.
            cash = coins * price * (1 - FEE_RATE)
            result.trades.append(("SELL", timestamp, price))
            coins = 0.0
            result.round_trips += 1
            if cash > last_buy_cost:
                result.wins += 1

        # Track the wallet's worth each candle to measure drawdown:
        # the deepest fall from a previous high point.
        equity = cash + coins * price
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak * 100
        result.max_drawdown_pct = max(result.max_drawdown_pct, drawdown)

        prev_signal = signal

    # Value everything at the last known price.
    last_price = df["close"].iloc[-1]
    result.final_value = cash + coins * last_price

    # Benchmark: buy on the first candle, hold to the end.
    first_price = df["close"].iloc[0]
    result.buy_hold_value = (STARTING_CASH * (1 - FEE_RATE) / first_price) * last_price

    return result


def print_report(result: Result, symbol: str, timeframe: str) -> None:
    print(f"\n=== Backtest: {symbol} on {timeframe} candles ===")
    print(f"Starting money:   ${STARTING_CASH:,.2f}")
    print(f"Trades made:      {len(result.trades)}")
    for action, ts, price in result.trades:
        print(f"  {action:4} {ts}  @ ${price:,.2f}")
    print(f"Final value:      ${result.final_value:,.2f}  ({result.profit_pct:+.2f}%)")
    print(f"Win rate:         {result.win_rate_pct:.0f}% of {result.round_trips} round trips")
    print(f"Max drawdown:     {result.max_drawdown_pct:.2f}%")
    print(f"Buy & hold value: ${result.buy_hold_value:,.2f}  ({result.buy_hold_pct:+.2f}%)")
    if result.final_value > result.buy_hold_value:
        print("The strategy BEAT buy-and-hold over this period.")
    else:
        print("The strategy did NOT beat buy-and-hold over this period.")
