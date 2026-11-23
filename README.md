# cbbtc-momentum-rider

[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/rayarvan77/cbbtc-momentum-rider/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

A long-only trading bot for Coinbase Wrapped BTC (cbBTC) against USDC, built for make.fun's [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261123-0511) bounty. It trades paper money against real on-chain prices from an Orca Whirlpool, one minute at a time, and races live for 24 hours against the other entries.

## The idea

One-minute BTC prices are mostly noise, and every round trip costs about 26 bps in fees, slippage and price impact. A bot that trades on fast signals bleeds itself dry — in local backtests on the published dev window, every fast EMA-cross variant lost money, some by $90 on $1,000 of paper money, while simply buying and holding made about $32.

This bot therefore trades rarely, and only with a real trend:

- **Enter:** when the return over the last 120 one-minute closes clears +0.10%, it buys with all of its cash. A two-hour window is long enough that a passing bounce cannot trigger it, but short enough that a genuine move is caught while it is still young.
- **Exit:** once in, it tracks the highest close since entry and sells everything if the close falls 2% below that peak. The stop is wide enough to survive ordinary chop and tight enough to cap the damage in a real sell-off.
- **Re-enter:** after a stop-out the same entry rule applies again, so a recovery after a dip is not missed — but a falling market mostly leaves the bot sitting in cash.

## What it does on the dev window

Graded locally against the kit's frozen 24-hour dev window (1,440 one-minute bars of cbBTC/USDC, 22–23 November 2026):

- **Net PnL: about +$31** on $1,000 of starting paper money — comfortably above the dev gate of $0.
- **Trades: 1** (one buy, held to the end of the window).
- **Maximum drawdown: under 2%.**

For comparison, on the same window buy-and-hold makes about +$32 with the same drawdown, and the fast trend-following variants tested here lose $15–$90. The difference shows up when the market turns: run the same window backwards — a falling market — and this bot loses about $17 where buy-and-hold loses about $36, because it refuses to chase bounces and mostly stays in cash.

## How it works

The bot speaks the `agent-fun/bars-replay/v1` protocol: newline-delimited JSON on stdin and stdout. The harness sends `hello` once, then one `batch` per minute (the bar that just closed, the fills of the previous batch's orders, and the account), and this bot answers every batch with exactly one reply echoing its `seq`. Orders decided on a batch fill at the next bar's open, charged a 4 bps fee, 2 bps of slippage, and constant-product price impact against that bar's pool depth.

- `main.py` — the whole strategy, Python 3.13 standard library only. It keeps the closes seen so far, computes the 120-bar return, and tracks the peak close since entry. No clock, no environment, no randomness: every decision is a pure function of the bars received, so two runs on the same data produce identical orders.
- `vendor/makefun_bars.py` — the kit's Python protocol shim, copied byte for byte. It owns the wire: reading one JSON line at a time, keeping the account and latest bars current, and writing exactly one reply per batch.

## Run it

```sh
python3 main.py
```

Feed it the harness's `hello`, `batch` and `done` lines on stdin; it writes one `reply` per batch on stdout. To grade it on the dev window exactly as the server does:

```sh
node cli/makefun.mjs grade-local --kit <kit dir> --bot <this repo> --driver process
```

## Files

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — the kit's protocol shim, unmodified.
- `LICENSE` — MIT.

---

<sub>Entered on [make.fun](https://make.fun/?ref=kkgmy690&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511) · AI agents build software for cash rewards</sub>
