---
name: etf-grid-operations-governance
description: "Use when governing ETF grid migrations or capital changes."
version: 1.0.0
---

# ETF Grid Operations Governance

Use this class-level skill alongside live ticket and state-management skills when a grid portfolio changes composition, reminder behavior, or capital policy. It governs authorization, sequencing, safety gates, and verification; it does not replace quote-specific ticket generation or fill booking.

## Core contract

Maintain three explicitly separate states:

1. **Broker state** — orders, cancellations, available T+1 inventory, frozen cash, and fills confirmed by the user from the broker.
2. **Local state** — ledger, tickets, reminder deduplication, and research reports.
3. **Authorization state** — what the user has actually approved: migration, new target buys, capital increase, gap change, or a third ETF.

A local guard may remove an order from recommendations, but it must never claim the broker order was cancelled. A touched price or alert is not a fill. A cron job reporting `ok` means the job ran, not that a Feishu message was delivered or an order executed.

## Migration workflow

For an authorized gradual migration from source ETF to target ETF:

1. Record the source, target, effective date, shared cost cap, unchanged holdings, cash floor, and whether target buys are enabled.
2. Put the source into **exit-only** mode: no new down-grid buys and no rebuy obligations generated from source sales.
3. Preserve legacy source buys in history for broker reconciliation; remove them from new recommendations and place them in an explicit withdrawal/reconciliation list.
4. Generate only source exit suggestions that pass T+1 available-pool and existing-resting-order checks. Do not invent target orders.
5. Before enabling target buys, require user/broker confirmation of source old orders, actual fills or cancellations, frozen funds, available cash, target quote timestamp, spread/premium/discount, and the shared cost cap.
6. When a source sale is confirmed, retire the named eligible grid lot and book the actual quantity and execution price. Do not create a source rebuy.
7. Keep unaffected ETFs on their existing policy; do not let migration logic rebase or alter them.

The live migration reference recipe is in `references/migration-and-reminder-gates.md`.

## Reminder scheduling

Use the user's established schedule only after checking the current schedule and delivery target:

- pre-market preview: local/silent, never executable;
- post-open operation suggestion: Feishu only after same-day 09:30+ live quote timestamps;
- intraday: every 10 minutes, only new touch alerts, deduplicated by trading day + code + direction + level;
- close review: Feishu, next-session non-executable reference only.

Holiday and non-session gates must run before loading the ledger or fetching quotes, including when a caller explicitly passes an execute phase. If the quote is stale, pre-open, or from the wrong date, downgrade to preview/quiet; never lock a limit from yesterday's close.

For day high/low alerts, disclose that the touch may have occurred before the recommendation was issued. The alert prompts a broker check and must not imply a fill.

## Capital-change governance

Treat “increase each grid amount” and “open a third ETF” as separate proposals, not automatic consequences of a migration. Until explicitly approved after the observation window:

- keep the existing account capital, gap, per-name caps, lot budgets, and cash floor;
- do not activate a research candidate as a position;
- do not multiply lot sizes merely because more capital is theoretically available;
- evaluate completed-cycle net spread, turnover, cash utilization, drawdown in currency, and missed opportunities before recommending a change.

## Whole-theme and cross-theme rotation governance

Same-theme ranking is not enough: an entire theme can become unsuitable because of narrow range, one-way trend, crowding, or a common macro shock. The weekly review must therefore run two layers against the same trailing common window (normally about 63 sessions):

1. compare the authorized baseline with eligible peers in the same theme;
2. compare the baseline with a pre-declared cross-theme set, such as broad index, coal, industrial metals, or media.

Keep these outcomes separate: same-theme leader, cross-theme leader, or no suitable leader/keep cash. Use the same gap, fee rule, capital constraint, cycle definition, and data basis. A close-only cycle count is a research proxy, not a fill. Do not select candidates only after seeing the result; record coverage and missing-data counts.

A candidate that leads only by completed-cycle count is not yet actionable. Before human rotation review, require the same candidate to lead in two consecutive weekly observations and then compare net completed-cycle spread, time-average inventory cost, downtrend inventory loss, liquidity/spread, tracking quality, and correlation with unchanged holdings. If no candidate clears these gates, keep cash.

A new cross-theme screen must not silently reverse an already-authorized migration such as 159992→589720. Preserve source exit-only mode, target authorization state, shared cost cap, and broker reconciliation requirements until the user explicitly changes them. See `references/theme-rotation-regime.md`.

## Testing and verification

Any change to reminder or migration logic should include isolated tests that:

- force a known exchange holiday and assert no ledger load or quote fetch;
- render a live post-open migration ticket and assert source buy/rebuy and target buy actions are absent;
- assert source exit and reconciliation language is present;
- verify the unaffected ETF remains in the ticket;
- compare checksums of the real ledger, active ticket, and intraday state before and after tests;
- run the full grid regression suite and record the real test count.

After changing cron configuration, read the job list back and verify schedule, delivery, script, enabled state, and next run. Cron success is not external delivery proof.

## Communication rules

Use concise, executable Chinese reminders with the user's established heading and product-name format. Always state “建议/核对”，not “已下单/已成交,” unless the broker confirmation exists. If multiple actions could have filled, require code, side, quantity, and actual execution price before booking. Keep capital-expansion alternatives explicitly undecided when the user has deferred them.

## Protected skill overlap

This skill complements the user-owned `etf-grid-ops`, `grid-trading-state-management`, and `grid-fill-confirm` skills. Do not edit those protected skills autonomously; use this governance layer for cross-cutting migration, scheduling, authorization, and verification lessons.
