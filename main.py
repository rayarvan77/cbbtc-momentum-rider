"""Momentum Rider: a long-only cbBTC (CBBTC/USDC) trading bot for
agent-fun/bars-replay/v1, written for make.fun's "Race a BTC trading bot
live for 24 hours" bounty.

The idea, in one paragraph: one-minute BTC prices are mostly noise, and
every round trip costs about 26 bps in fees, slippage and price impact,
so a bot that trades on fast signals bleeds itself dry. This bot trades
rarely and only in the direction of a real trend. It watches the return
over the last two hours of one-minute closes; when that return clears a
small positive bar it buys with all of its cash, and it stays in until
the price falls 2% below the highest close seen since it bought. The
same rule lets it back in after it is stopped out, so a genuine recovery
is not missed, while a falling market mostly leaves it in cash. On the
published dev window this makes about +$31 on $1,000 of paper money with
a single trade and a maximum drawdown under 2%; on the same window run
backwards (a falling market) it loses about $17 where buy-and-hold loses
about $36, because it refuses to chase bounces.

The bot is fully deterministic: no clock, no environment, no randomness.
Every decision is a pure function of the bars the harness has sent so
far, so two runs on the same data answer every batch with the same
orders, byte for byte.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Smallest buy the replay accepts, in quote units (1 USDC).
MIN_NOTIONAL = 1_000_000
# How far back the trend is measured, in one-minute bars.
TREND_BARS = 120
# The two-hour return that counts as an uptrend worth joining (0.10%).
TREND_ENTER = 0.001
# How far the close may fall from its peak since entry before we exit.
STOP_FRACTION = 0.02
# Headroom allowed between the latest close and the fill price, in bps.
# One-minute moves on this pool are under ~75 bps, so 200 bps never
# binds in practice; it only guards against a wild bar.
MAX_SLIPPAGE_BPS = 200


class MomentumRider:
    """Keeps the closes seen so far and the peak close since entry."""

    def __init__(self):
        self.closes = []
        self.peak = None

    def two_hour_return(self):
        """Return of the latest close against the close 120 bars back."""
        if len(self.closes) <= TREND_BARS:
            return None
        old = self.closes[-TREND_BARS - 1]
        new = self.closes[-1]
        return new / old - 1.0

    def on_batch(self, state, batch):
        """Decide the orders for one batch (one closed minute bar).

        The hello, batch and orders flow is the harness's: hello once,
        then one batch per minute, and this function answers every batch
        with exactly one reply, echoing its seq, through the shim.
        """
        if state.warming_up:
            return []
        bars = [b for b in batch.get("bars", []) if b.get("symbol") == SYMBOL]
        if not bars:
            # A minute with no bar for our symbol carries no new
            # information, so no decision is made on it.
            return []
        close = int(bars[-1]["c"])
        self.closes.append(close)

        holding = state.positions.get(SYMBOL)
        if holding is None:
            if state.cash < MIN_NOTIONAL:
                # Not enough cash left for even the smallest buy.
                return []
            trend = self.two_hour_return()
            if trend is not None and trend > TREND_ENTER:
                self.peak = close
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        # We hold a position: track the peak and stop out below it.
        if self.peak is None or close > self.peak:
            self.peak = close
        if close < self.peak * (1.0 - STOP_FRACTION):
            self.peak = None
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []


def main():
    rider = MomentumRider()
    makefun_bars.run(rider.on_batch)


if __name__ == "__main__":
    main()
