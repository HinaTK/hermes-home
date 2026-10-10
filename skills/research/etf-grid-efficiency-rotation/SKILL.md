---
name: etf-grid-efficiency-rotation
description: "Use when reviewing ETF grid efficiency or rotation."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [ETFs, grid-trading, rotation, monitoring, research]
---

# ETF Grid Efficiency and Rotation

## Purpose

Class-level workflow for deciding whether an active ETF grid is becoming inefficient and whether a same-class ETF merits a staged rotation review. This skill is for research, monitoring, and governance. It does not place broker orders, cancel orders, book fills, or activate a target ETF.

## Core distinction

A low number of grid events is not automatically low volatility. Separate:

- **Narrow range:** price does not cover the active grid spacing.
- **Uptrend:** the grid may sell winners but fail to rebuy; the issue is opportunity cost, not necessarily low volatility.
- **Downtrend:** buys may fill without exits; the issue is inventory, cash, and drawdown risk.

Use completed buy→sell round trips as the primary operational efficiency measure. Do not count touches, alerts, resting orders, generated tickets, or one-way initial-inventory sales as completed cycles.

## Daily after-close review

For each active ETF, use the local confirmed-fill ledger and confirmed current-session market data:

1. Pair only successful, user/broker-confirmed buys and sells. Preserve the distinction between a grid target/level and the actual pooled inventory lot consumed at sale.
2. Compute a trailing **20 confirmed trading-session** window and report:
   - completed cycles in 20 sessions;
   - completed cycles in the trailing 10 sessions;
   - **grid crossings**: how many times price moved >= gap from the last crossing level (not max/min range);
   - **trend ratio**: fraction of recent closes above the 20-day MA;
   - data coverage and stale/missing-data state.

### Pitfall: max/min range is misleading

`max(closes) / min(closes) - 1` only captures the extreme high and low. A price that oscillates 1.00→1.03→1.00→1.03 produces the same range as a single spike 1.00→1.045→1.00, but the first is genuinely grid-friendly and the second is not. Always use **grid crossings** (cumulative >= gap moves from the last crossing level) instead of max/min range for efficiency assessment. Same for trend: comparing only the first and last close in a window misclassifies volatile ranges as RANGE. Use the fraction of recent closes above the 20-day MA instead.
3. Flag a non-executable efficiency review if cycles are <=1 in 20 sessions or zero in 10 sessions. A warning is not a switch recommendation.
   - If crossings <= 1, state explicitly that the price has not covered the grid spacing — this is genuine low volatility, not a trend or execution issue.
   - If crossings > 1 but cycles are low, the issue is likely trend (opportunity cost or inventory risk), not low volatility.
4. If fewer than 20 confirmed sessions exist, the last bar is not a confirmed close, dates are duplicated/out of order, or the quote is stale, return DATA_INSUFFICIENT. Do not infer low volatility.
5. Keep this review ahead of any optional rebasing discussion. If an ETF is in an authorized exit-only migration, migration policy takes precedence over rebasing or rebuys.

## Weekly same-class comparison

1. Freeze the portfolio baseline first. For the current authorized migration, 589720 is the innovation-drug baseline replacing 159992; 159992 remains exit-only.
2. **The candidate pool must include every live holding, not just same-class peers.** A hardcoded theme list that omits currently-held ETFs (e.g. 159363 创业板人工智能, 159992 创新药) silently drops them from the ranking and makes the report look as if they don't exist. Always maintain a `HOLDINGS` list — current positions that are fetched, simulated, and reported regardless of which theme bucket they fall into. Holdings are shown for reference and never trigger a switch review on their own.
3. Compare every eligible same-class candidate over the same trailing **63 confirmed sessions**, approximately three months. Preserve coverage, liquidity, exclusions, and failures; do not hand-pick a winner.
4. Use a fully specified executable model where available. A close-only 2% cycle proxy is acceptable for preliminary ranking only and must be labeled as a proxy: it does not establish intraday order, actual fills, T+1 availability, spread, slippage, or broker feasibility.
5. Persist weekly state by candidate, date, baseline, window, method, and errors.
6. Only if the **same candidate** beats the baseline in completed-cycle count in two consecutive weekly observations should the report say HUMAN_ROTATION_REVIEW. Otherwise report observation only.
7. Even after that threshold, require a human review of liquidity, bid-ask spread, fund operation, tracking error, shared-index correlation, shared cost cap, cash floor, fees, T+1, current quote timestamp, frozen cash, existing broker orders, and available shares.

## Two research scripts — do not confuse them

The system has two separate ETF research scripts. They answer different questions and must not be merged.

| | Full-market study | Weekly rotation check |
|---|---|---|
| Script | `cache/grid-third-20260930/research.py` | `scripts/grid_weekly_rotation.py` |
| Candidate pool | **321 ETFs** (full eligibility table) | **321 ETFs** (same eligibility table, re-fetched every run) |
| Data | 5-minute bars, 104 sessions | Daily closes, 63 trailing sessions |
| Window | Fixed 2026-04-24 → 2026-09-22 | Rolling, updated every Friday |
| Fees | Two tiers: 万0.1 and 万1 | Not modelled (close proxy) |
| Model | `grid_model.py` (slippage, T+1, inventory) | `simulate_daily_grid()` (4 parallel slots) |
| Output | `ranking-all-321.csv`, `summary.json` | `rotation/YYYY-MM-DD.json`, weekly report |
| Purpose | One-time full-market ranking; answers "which ETFs are grid-friendly across the whole market" | Recurring weekly screen; re-runs the full 321 pool on the latest trailing window |

**The weekly check uses the same 321-ETF eligibility pool as the full-market study** (`cache/grid-broad-20260923/eligibility.csv`). It re-fetches daily closes for all 321 and re-simulates the trailing 63 sessions every run. It is NOT limited to a 13-ETF theme list — that was a bug that silently dropped live holdings (159363, 159992) from the ranking.

The full-market study is authoritative for **absolute** rankings (321 ETFs, 5-min data, two fee tiers). The weekly check is authoritative for **relative change** (same 321 pool, same window, week-over-week, same model). When the user asks "what's the ranking", the weekly check re-runs the full pool on the latest window — do not cite the frozen `ranking-all-321.csv` unless the user explicitly asks for the historical one-shot result.

The full-market study does not need to be re-run — its window has expired and re-running 321 ETFs × 8 runs each is expensive. Its results are frozen in `ranking-all-321.csv` for historical reference only.

## Migration and authorization gates

Maintain three states separately: broker state, local state, and authorization state. A local exit-only guard does not prove a broker cancellation. A target appearing in a research report does not authorize a purchase. A threshold crossing means review is due, not that a switch or order is approved.

For a staged migration:

- source ETF: stop new buys and post-sale rebuys; preserve existing inventory for orderly exit;
- target ETF: remain research-only until old orders, fills/cancellations, frozen funds, available cash, quote timestamp, spread/premium/discount, and shared cost cap are reconciled;
- unaffected ETF: retain its existing policy;
- account capital, grid gap, per-name/group caps, lot budgets, and cash floor remain unchanged unless explicitly authorized.

## Evidence and reporting

Separate actual realized P&L, mark-to-market inventory P&L, and proxy cycle counts. State whether the result uses confirmed fills, daily closes, or an executable simulation. Overlapping 63-session windows are correlated and are not independent trials. Historical leaders do not guarantee future turnover.

A report should include: baseline, candidates and exclusions, common window, method, completed-cycle counts, leader and count gap, consecutive-week state, data errors, path classification, downside/inventory interpretation, and the exact next review trigger.

## Verification

When changing an existing monitoring workflow:

- write behavior tests for cycle counting, insufficient data, same-candidate consecutive-week persistence, same-day rerun idempotence, candidate changes resetting the streak, and migration precedence;
- run the focused tests and the existing grid regression suite;
- compile/run the production scripts;
- read back scheduled jobs and verify schedule, delivery target, enabled state, script, and workdir;
- never claim a cron `ok` proves Feishu delivery or broker execution.

See `references/rotation-efficiency-review.md` for thresholds, state fields, and a reusable implementation outline.

See `references/grid-crossings-and-trend.md` for the algorithm behind grid crossings and trend ratio, including why max/min range is misleading.

## Implementation reference

The production implementation lives in `scripts/grid_rotation_review.py`. Key functions:

- `count_grid_crossings(closes, gap)` — cumulative >= gap moves from last crossing level. Replaces max/min range.
- `recent_trend_ratio(closes, lookback=10)` — fraction of recent closes above 20-day MA. Replaces first/last close direction.
- `assess_low_efficiency(cycles, bars, day, gap)` — returns state, cycles_20d, cycles_10d, crossings, trend_ratio, reason.
- `completed_cycles(book, code)` — pairs confirmed buys/sells by lot from the ledger history.

Tests in `scripts/test_grid_rotation_review.py` cover: cycle pairing, insufficient data, crossings vs max/min range distinction, trend ratio, consecutive-week persistence, and cross-theme screening.
