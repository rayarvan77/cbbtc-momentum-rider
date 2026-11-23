"""cbBTC momentum rider: a long-only, single-asset trading bot for the
make.fun "Race a BTC trading bot live for 24 hours" competition.

The idea is deliberately small. Coinbase Wrapped BTC usually drifts in
quiet stretches and then jumps in short bursts, so this bot waits for a
clear two-hour push before it buys, and it gets out as soon as the price
gives back a meaningful part of its run-up. It holds at most one
position, trades at most once per minute bar, and never uses leverage,
shorts, the clock, the environment, or randomness: every decision is a
pure function of the CBBTC closes the harness has sent so far.

Rules, in plain words:

* Watch the CBBTC close of every minute bar and remember them all.
* Flat: once at least 121 closes are known, compare the newest close
  with the close 120 bars earlier. If it is up by more than 0.10%,
  spend all available cash on CBBTC (a buy is skipped when the cash
  left is under 1 USDC, the minimum notional).
* Holding: keep the highest close seen since the entry. If the newest
  close drops more than 2% below that peak, sell the whole position.
  After a sale the entry rule applies again, so the bot can re-enter
  on the next qualifying push.
* Batches with no CBBTC bar, and warm-up batches, are ignored.

The entrypoint is this file, run as ``python3 -P -s main.py``. It
speaks agent-fun/bars-replay/v1 through the vendored shim in
``vendor/makefun_bars.py`` (a byte-for-byte copy of the kit's Python
shim), one reply per batch.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# How far back the momentum look-back reaches, in bars (two hours).
MOMENTUM_BARS = 120
# Entry needs a return strictly above this, in basis points (0.10%).
ENTRY_MIN_BPS = 10
# Exit when the latest close is more than this below the peak since
# entry, in basis points (2%).
EXIT_DROP_BPS = 200
# Largest slippage the bot will tolerate on any fill, in basis points.
MAX_SLIPPAGE_BPS = 200
# Minimum cash (quote units) worth spending on a buy: 1 USDC.
MIN_BUY_QUOTE_UNITS = 1_000_000


class Rider:
    """The bot's memory: every CBBTC close seen, and the peak since entry."""

    def __init__(self):
        self.closes = []
        self.peak = None

    def note_bar(self, close):
        """Record one CBBTC close; while holding, refresh the peak."""
        self.closes.append(close)
        if self.peak is not None and close > self.peak:
            self.peak = close

    def momentum_above(self):
        """True once at least 121 closes exist and the latest close sits
        strictly more than 0.10% above the close 120 bars earlier.
        Compared exactly in integers, so a return of 10.4 bps counts."""
        if len(self.closes) <= MOMENTUM_BARS:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - MOMENTUM_BARS]
        return now * 10_000 > then * (10_000 + ENTRY_MIN_BPS)

    def dropped_below_peak(self):
        """True while holding and the latest close has fallen strictly
        more than 2% below the highest close since entry."""
        if self.peak is None or not self.closes:
            return False
        latest = self.closes[-1]
        return (self.peak - latest) * 10_000 > self.peak * EXIT_DROP_BPS


RIDER = Rider()


def on_batch(state, batch):
    """Decide this minute's orders from the bars received so far."""
    if state.warming_up:
        return []

    bar = state.latest.get(SYMBOL)
    if bar is None:
        # No CBBTC bar in this batch: nothing to learn, nothing to do.
        return []

    holding = state.positions.get(SYMBOL)
    if holding is None and RIDER.peak is not None:
        # A sale went through on the previous batch: the peak belongs to
        # the closed trade, so forget it before judging a fresh entry.
        RIDER.peak = None

    RIDER.note_bar(int(bar["c"]))

    if holding is not None:
        # We own CBBTC: leave only on a real give-back from the peak.
        if RIDER.dropped_below_peak():
            RIDER.peak = None
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Flat: buy the whole cash pile on a fresh two-hour push.
    if not RIDER.momentum_above():
        return []
    if state.cash < MIN_BUY_QUOTE_UNITS:
        return []
    RIDER.peak = RIDER.closes[-1]
    return [{
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": state.cash,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


makefun_bars.run(on_batch)
