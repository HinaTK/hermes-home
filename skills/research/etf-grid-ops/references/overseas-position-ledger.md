# Overseas (non-grid) position ledger — 海外趋势持有账本

Class: the user runs buy-and-hold / tranche plans on QDII ETFs (Nikkei 159866, Nasdaq 513300 pending) OUTSIDE the grid account. These positions need their own ledger, their own trigger monitor, and must never touch the grid ledger's T+1/00:01/intraday chain.

## Ledger shape (2026-11-03 first fill)

File: `HERMES_HOME/cache/grid-account/overseas-positions.json` (same cache dir, deliberately separate file — the grid rollover script iterates `confirmed-*.json` sub-ledgers and must skip this one).

Per code:
- `plan`: one-line description of the tranche plan with all trigger prices and the stop rule.
- `lots[]`: per-fill records — tranche number, date, side, qty, price, amount, commission, total_cost, available_from (T+1 date), note (which monitor trigger produced it).
- Aggregates: `qty`, `total_cost`, `unit_cost` (= total_cost/qty, fee-inclusive), `budget` (total plan budget), `realized`.

## Fill acceptance flow (per tranche, 2026-11-03 Nikkei T1)

1. **Verify against live quote** before booking: user-reported fill price vs current price / day low (9000@1.600 booked while spot 1.591, day low 1.599 — inside the tranche band, sane).
2. Book into `overseas-positions.json` with computed fee (万一, min 1 元): `total_cost = qty×price + max(amount×0.0001, 1)`.
3. **Advance the monitor**: delete the filled tranche's branch, point the trigger line at the next tranche (T2 ≤1.52, T3 ≤1.42 for Nikkei). Keep `min(price, day_low)` touch detection so an intraday spike-and-recover is not missed.
4. **Clean the state file**: remove the filled trigger from `active[]` and its per-day dedup key — otherwise the next run emits a spurious "触发已解除" notification for a tranche that was intentionally filled.
5. Report: fill row + unit cost + remaining budget + remaining tranches with distances + stop line (weighted cost × 0.75). All numbers script-computed, never mental arithmetic.

## Distinct from grid fills

- No grid letters, no rebuy obligation, no max_grid pointer.
- Commission is 万一免五 (min 1元) — same rate as grid but book it in this ledger.
- The 00:01 grid rollover does NOT touch this file; T+1 availability is per-lot `available_from` only.
- The grid account summary (`grid_summary.py` iterates `confirmed-*.json`) does not include these positions — report them separately when the user asks for "all holdings".

## Monitor mechanics (overseas_trigger_monitor.py, cron 9b7100f3c8b1)

- Nasdaq 513300: premium <5% (plan-start signal) and NAV drawdown from 1y peak ≥8% (add-on signal), NAV via 天天基金 pingzhongdata `Data_netWorthTrend`, spot via Tencent.
- Nikkei 159866: tranche ladder (T2/T3 after T1 filled 2026-11-03), touch = min(price, day_low), quote-time gate (same-day snapshot, ≥09:30) to avoid yesterday-extreme false fires.
- Watchdog discipline: silent when nothing fires; state-flip only (new trigger → push once; resolved → push once).

## Commission/price verification rule

User-reported fills are booked at the reported price with computed fee. Cross-check the price against the tranche band and same-day quote; if the reported price is outside the band or the day's range, flag 待核 before booking rather than silently accepting.
