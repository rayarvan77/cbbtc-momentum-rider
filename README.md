[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

# cbbtc-momentum-rider

A long-only trading bot for Coinbase Wrapped BTC (cbBTC) against USDC,
entered in the make.fun bounty
[Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261123-0511).

## The idea

cbBTC usually drifts sideways for hours and then moves in short bursts.
Round 1 of this entry bought the burst and held it to the end of the
day; that works when the day has one clean rise, and it is helpless
when it does not. Round 2 keeps the patient entry and adds a way out:
bank the gain once it reaches +2%, sit out for an hour, and only come
back on a fresh push. The bot trades the same move in legs instead of
betting the whole day on a single hold.

## Strategy

Starting from $1,000 of paper money:

1. **Watch.** Remember the close of every CBBTC minute bar.
2. **Enter (flat only).** Once at least 121 closes are known, compare
   the newest close with the close 120 bars earlier. If it is up by
   more than 0.30%, buy CBBTC with all available cash
   (`max_slippage_bps` 200). A buy is skipped when the cash left is
   under 1 USDC. The 0.30% bar sits above the ~26 bps a full round
   trip costs in fee, slippage and price impact, so a trade that
   clears it can pay for itself.
3. **Bank the gain (holding only).** If the newest close reaches 2%
   above the close the position was bought at, sell the whole
   position.
4. **Disaster exit (holding only).** Track the highest close since
   entry. If the newest close falls more than 2% below that peak,
   sell the whole position.
5. **Wait (flat, after a sale).** For 60 bars after a sale the entry
   rule stays off. Buying back the next minute would just repay the
   round-trip fee for the same position at the same price; the wait
   means the next entry is a fresh signal, often at a better price.
6. **Repeat.** After the wait the entry rule applies again, so the bot
   can ride a second leg of the same day.

Batches with no CBBTC bar and warm-up batches are ignored. The bot is
fully deterministic: no clock, no environment reads, no randomness. If
a sell is rejected, the trailing stop is re-armed from the latest close
so the exit retries instead of holding to the end of the window.

## What the sweeps showed

Every number below comes from a local simulator that copies the kit's
fill model exactly (fill at the next bar's open, 4 bps fee, 2 bps
slippage, constant-product price impact). Full sweep tables live in
`analysis/sweep-results-r2/` in the workdir, not in this repo.

- **The dev day has one real move.** A strong rise early in the day,
  then sideways chop. Every strategy that catches the rise and holds
  it makes about +$30; every strategy that keeps trading the chop
  gives the money back in fees.
- **Momentum-reversal exits were tested and rejected.** Exiting when
  the 120-minute momentum turns negative churns 7–11 trades and ends
  between −$5 and +$8, losing in the second half of the day. Short
  30/60-minute reversal exits are worse (−$27 to −$82). The
  take-profit exit above is what the data supports instead.
- **Tighter trailing stops were tested and rejected.** A 1.2–1.5%
  stop makes 5–7 trades but loses $6–19 in the second half.
- **The chosen parameters sit on a plateau.** Take-profit 2.0% with a
  60-bar wait makes +$41.04; its neighbours (take-profit 1.5% and
  2.5%, waits of 30 and 60 bars, entry 0.25% and 0.35%) all stay
  profitable at +$15 to +$38, win the first half of the day, and lose
  on time-reversed data — the edge is directional, not an artefact.
- **At double the fee and slippage the chosen bot still makes
  +$37.31**, so a thinner pool on race day does not flip it.

## Dev-window result

Graded locally on the kit's published 24-hour dev window (1,440
one-minute bars) with the driver's fill model, the bot finishes with a
net PnL of **+$41.04 on 5 fills** (buy, take-profit, buy the dip,
take-profit, buy again and hold to the close), with a maximum drawdown
of 1.58%. That clears the dev gate (net PnL above $0), so the entry
races. The dev window never counts toward the ranking; the race window
alone decides it, and a quiet or falling day there could just as well
leave this bot flat or in the red. Five fills on one day is still a
thin basis for confidence, and the result above should be read as
exactly that: one backtest, not a promise.

## How it runs

The entrypoint is `main.py` (Python 3.13, standard library only). It
speaks the `agent-fun/bars-replay/v1` protocol through the vendored
shim `vendor/makefun_bars.py`, a byte-for-byte copy of the kit's Python
SDK shim. The harness sends one batch per minute bar and the bot
answers each with exactly one reply.

## Layout

- `main.py` — the bot: close history, momentum entry, take-profit and
  trailing-peak exits, one-hour wait after a sale.
- `vendor/makefun_bars.py` — the protocol shim (kit copy, not authored
  here).
- `LICENSE` — MIT.

## License

MIT — see [LICENSE](LICENSE).
