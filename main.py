"""cbBTC momentum rider, round 2: catch a real two-hour push, bank the gain
at +2%, and only come back after an hour has passed.

The dev window for this race has one shape that matters: a single strong
rise early in the day, then hours of sideways chop. A bot that buys the
rise and simply holds it does fine, but it has no way out if the race
day turns, and it bets everything on one trade. This version keeps the
same patient entry and adds two exits that the sweep data actually
supports:

* Enter flat only. Once 121 closes are known, compare the newest close
  with the close 120 bars earlier. Buy with all cash only if the rise
  is more than 0.30% -- above the ~26 bps a full round trip costs in
  fee, slippage and price impact, so a marginal trade can pay for
  itself.
* While holding, bank the gain: sell the whole position as soon as the
  newest close is at least 2% above the close the bot bought at.
* While holding, the disaster exit stays: sell if the newest close
  falls more than 2% below the highest close since entry.
* After any sale, sit out for 60 bars. Buying back the very next minute
  just repays the round-trip fee for the same position at the same
  price; waiting for a fresh momentum signal buys the dip instead.
  The entry rule applies again after the wait, so the bot can ride a
  second leg.

Everything is a pure function of the CBBTC closes the harness has sent
so far: no clock, no environment, no randomness, no leverage, no short,
one position at a time. It speaks agent-fun/bars-replay/v1 through the
vendored shim in ``vendor/makefun_bars.py`` (a byte-for-byte copy of the
kit's Python shim), one reply per batch.

Two details protect the exit. If a sell is rejected, the peak is
re-armed from the latest close so the exit can retry on the next batch
instead of holding to the end of the window, and the entry price is kept
so the take-profit check still applies to the same position. If a buy is
rejected, the peak and entry price are forgotten as soon as the next
batch shows no position, so no stale state can trigger a phantom exit.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# Two-hour look-back for the entry signal, in bars.
MOMENTUM_BARS = 120
# Entry needs a rise strictly above this, in basis points (0.30%).
ENTRY_MIN_BPS = 30
# Bank the gain once the close is at least this far above the entry
# close, in basis points (2%).
TAKE_PROFIT_BPS = 200
# Disaster exit: sell when the close is more than this below the peak
# since entry, in basis points (2%).
EXIT_DROP_BPS = 200
# Bars to sit out after a sale before the entry rule may fire again.
COOLDOWN_BARS = 60
# Largest slippage the bot will tolerate on any fill, in basis points.
MAX_SLIPPAGE_BPS = 200
# Minimum cash (quote units) worth spending on a buy: 1 USDC.
MIN_BUY_QUOTE_UNITS = 1_000_000


class Rider:
    """The bot's memory: every CBBTC close seen, the peak and entry close
    of the open trade, and how long the last sale was ago."""

    def __init__(self):
        self.closes = []
        self.peak = None
        self.entry = None
        self.last_sell_len = None

    def note_bar(self, close):
        """Record one CBBTC close; while holding, refresh the peak."""
        self.closes.append(close)
        if self.peak is not None and close > self.peak:
            self.peak = close

    def momentum_above(self):
        """True once at least 121 closes exist and the latest close sits
        strictly more than 0.30% above the close 120 bars earlier.
        Compared exactly in integers, so a rise of 30.4 bps counts."""
        if len(self.closes) <= MOMENTUM_BARS:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - MOMENTUM_BARS]
        return now * 10_000 > then * (10_000 + ENTRY_MIN_BPS)

    def take_profit_hit(self):
        """True while holding and the latest close is at least 2% above
        the close the position was bought at."""
        if self.entry is None or not self.closes:
            return False
        latest = self.closes[-1]
        return latest * 10_000 >= self.entry * (10_000 + TAKE_PROFIT_BPS)

    def dropped_below_peak(self):
        """True while holding and the latest close has fallen strictly
        more than 2% below the highest close since entry."""
        if self.peak is None or not self.closes:
            return False
        latest = self.closes[-1]
        return (self.peak - latest) * 10_000 > self.peak * EXIT_DROP_BPS

    def cooling_down(self):
        """True while fewer than 60 bars have passed since the last sale
        was decided."""
        if self.last_sell_len is None:
            return False
        return len(self.closes) - self.last_sell_len < COOLDOWN_BARS


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
    if holding is None and (RIDER.peak is not None or RIDER.entry is not None):
        # No position: the peak and entry price belong to a closed
        # trade (or a rejected buy), so forget them before judging a
        # fresh entry.
        RIDER.peak = None
        RIDER.entry = None

    RIDER.note_bar(int(bar["c"]))

    if holding is not None and RIDER.peak is None:
        # A sell was rejected after the peak was cleared: re-arm the
        # trailing stop from the latest close so the exit can retry
        # instead of holding to the end of the window. The entry price
        # stays, so the take-profit check still covers this position.
        RIDER.peak = RIDER.closes[-1]

    if holding is not None:
        # We own CBBTC: leave on a banked gain, or on a real give-back
        # from the peak. Either way the sale starts the cooldown.
        if RIDER.take_profit_hit() or RIDER.dropped_below_peak():
            RIDER.peak = None
            RIDER.last_sell_len = len(RIDER.closes)
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Flat: buy the whole cash pile on a fresh two-hour push, once the
    # cooldown after the last sale has run out.
    if RIDER.cooling_down():
        return []
    if not RIDER.momentum_above():
        return []
    if state.cash < MIN_BUY_QUOTE_UNITS:
        return []
    RIDER.peak = RIDER.closes[-1]
    RIDER.entry = RIDER.closes[-1]
    return [{
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": state.cash,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


makefun_bars.run(on_batch)
