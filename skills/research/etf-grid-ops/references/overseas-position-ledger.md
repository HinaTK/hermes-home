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

- Nasdaq 513300 (premium rules tightened 2026-11-04, user decision 跨境溢价>3%放弃): start signal = premium <3%; add-on signal = NAV drawdown from 1y peak ≥8% **AND** premium <3%. Premium is a HARD gate, not advisory text — at premium ≥3% both signals are fully silent. The old <5% start line is abolished. NAV via 天天基金 pingzhongdata `Data_netWorthTrend`, spot via Tencent.
- Nikkei 159866: tranche ladder (T2/T3 after T1 filled 2026-11-03), touch = min(price, day_low), quote-time gate (same-day snapshot, ≥09:30) to avoid yesterday-extreme false fires. Buy tranches are gated by premium >2% (2026-11-04 user decision: no new buys/adds when exceeded); the stop line is checked BEFORE the premium gate and is never premium-gated. If the NAV source fails (premium = None) the gate is soft — record None, do not hard-block; the user still has same-day live IOPV as the final manual check before executing.
- Live state file (migrated 2026-11-04): `D:/Code/AH_analyse/.cache/grid-home/cache/grid-account/overseas-triggers.json` (the ledger root named by run_and_push.py; copy-not-cut, hermes side kept as frozen backup). The hermes-side `HERMES_HOME/cache/grid-account/overseas-triggers.json` is a FROZEN pre-migration snapshot — diagnosing from it gives stale `active[]` (after the gate voided `nasdaq_drawdown` it still listed that key). Always read the AH-side live file.
- Watchdog discipline: silent when nothing fires; state-flip only (new trigger → push once; resolved → push once).

## Commission/price verification rule

User-reported fills are booked at the reported price with computed fee. Cross-check the price against the tranche band and same-day quote; if the reported price is outside the band or the day's range, flag 待核 before booking rather than silently accepting.

## Exit semantics — what "一直拿着" actually means (2026-11-03 user confirmation)

User asked "这个就是一直拿着的是吗？除非到止损线？" — confirmed management model, encode it for future "什么时候卖" questions:

- **Add-on tranches are not sells**: dropping into the T2/T3 bands is buying (cost averaging), never an exit trigger.
- **Stop line (weighted cost × 0.75) is a re-evaluation line, not a mechanical sell**: when hit, the thesis is presumed broken — lay out why it fell / how much / stay-vs-leave for the user to decide. No script auto-liquidates. The line is RECOMPUTED after each new tranche fills (lower fills pull weighted cost down, moving the absolute stop).
- **No fixed take-profit on the upside**: index positions ride the whole trend; a target price amputates the fat tail. Upside exits are managed by trend-break rules (same family as the Nasdaq plan's "drawdown from 1y peak ≥8%"), pushed to the user when triggered.
- Between the lines the user does nothing; the 10-minute monitor owns both lower boundaries.

## Tranche advance must realign companion tests (2026-11-03 incident)

The commit that switched the monitor to T2/T3 left `test_overseas_trigger_monitor.py` in the T1 era — 3 of 9 red, discovered during a routine state check. Rules:

- Editing the monitor's TRANCHES ladder is a behavior change → realign the test file in the SAME change (RED→GREEN, per the user's standing TDD mandate).
- Encode the ladder priority semantic in tests: `break` fires only the FIRST unfilled tranche — a deep day-low touching both T2 and T3 levels pushes T2 alone; T3's line arms only after T2 is booked.
- Running the monitor's test file is part of any monitor health check — a red suite means deployed logic and its spec have drifted.

## Rule tightening that voids an active trigger → one-time "已解除" transitional noise (2026-11-04 incident)

Deploying a new hard gate (or any rule change) that newly suppresses a signal already sitting in the state file's `active[]` makes the state-flip loop push a single "ℹ️ 触发已解除：<key>" on the next run. Real case: the 2026-11-04 premium gate went live at 09:31; legacy `nasdaq_drawdown` (recorded 11-03 under no-gate rules: drawdown -10.4% met the add-on line but premium was +12.8%) was voided by the gate, and the 09:40 run pushed "触发已解除" — the user read it as an alarm and asked "这是触发了什么 我没看懂".

Rules:
- **"触发已解除" right after a rule change means "the old signal was voided by the new rule", NOT "all clear / safe to buy".** Say this explicitly so the user cannot misread the direction.
- When deploying a gate that will suppress a known-active trigger: pre-clear that key from `active[]` in the same change, or warn the user the one-shot "已解除" push is coming and what it means.
- When the user asks what a monitor push meant, diagnose from evidence, then answer conclusion-first in plain language: (1) per-run files in the cron output dir for job `9b7100f3c8b1` (each shows silent vs fired, the exact message and fire time), (2) the LIVE AH-side state file, (3) the currently-deployed script's rules. Translate the machine message into what it means for money: "no action needed / old advice voided / real signal — act". The job is silent unless something actually fires, so an unexplained push always has a one-line cause in one of those three places.
