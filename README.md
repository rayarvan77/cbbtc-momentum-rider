[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

# cbbtc-momentum-rider

A long-only trading bot for Coinbase Wrapped BTC (cbBTC) against USDC,
entered in the make.fun bounty
[Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261123-0511).

## The idea

cbBTC usually drifts sideways for hours and then moves in short bursts.
This bot does not try to catch every wiggle; it waits for a clear
two-hour push, rides it with the whole cash pile, and steps out as soon
as the price gives back a real part of its run-up. One position at a
time, no leverage, no shorts, and no guessing: every decision is a pure
function of the minute bars the replay has sent so far.

## Strategy

Starting from $1,000 of paper money:

1. **Watch.** Remember the close of every CBBTC minute bar.
2. **Enter (flat only).** Once at least 121 closes are known, compare
   the newest close with the close 120 bars earlier. If it is up by
   more than 0.10%, buy CBBTC with all available cash
   (`max_slippage_bps` 200). A buy is skipped when the cash left is
   under 1 USDC.
3. **Exit (holding only).** Track the highest close since entry. If
   the newest close falls more than 2% below that peak, sell the
   whole position (`max_slippage_bps` 200).
4. **Repeat.** After a sale the entry rule applies again, so the bot
   can re-enter on the next qualifying push.

Batches with no CBBTC bar and warm-up batches are ignored. The bot is
fully deterministic: no clock, no environment reads, no randomness.

## Dev-window result

Graded locally on the kit's published 24-hour dev window (1,440
one-minute bars) with the driver's fill model, the bot finishes with a
net PnL of about **+$31** on **1 trade**, with a maximum drawdown under
2%. That clears the dev gate (net PnL above $0), so the entry races.
The dev window never counts toward the ranking; the race window alone
decides it, and a single quiet day there could just as well leave this
bot flat or in the red. One trade on one day is a thin basis for
confidence, and the result above should be read as exactly that: one
backtest, not a promise.

## How it runs

The entrypoint is `main.py` (Python 3.13, standard library only). It
speaks the `agent-fun/bars-replay/v1` protocol through the vendored
shim `vendor/makefun_bars.py`, a byte-for-byte copy of the kit's Python
SDK shim. The harness sends one batch per minute bar and the bot
answers each with exactly one reply.

## Layout

- `main.py` — the bot: close history, momentum entry, trailing-peak exit.
- `vendor/makefun_bars.py` — the protocol shim (kit copy, not authored here).
- `LICENSE` — MIT.

## License

MIT — see [LICENSE](LICENSE).
