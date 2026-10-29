# EOD daily report tables (15:20 push)

Session rule 2026-10-26 (user: “我要的是做成表格，告诉我总的做T情况以及当天的做T情况，这两个都可以通过脚本得出”): the daily EOD push must be tables — cumulative T and today's T — both produced by script, never hand-assembled.

## Chain

cron b3097b45fafa (weekdays 15:20) → `scripts/grid_eod_decision.py` → `confirmed_runtime.eod_main(render=True)` → `eod_report()` → `render_eod()`

- `grid_summary.summarize_account(root)` reads every `confirmed-*.json` sub-ledger: per-ETF totals plus `daily[day]` buckets.
- `_daily_stats` keys a completed round to the **SELL trade's date** (round completes when the sell fills); a rebuy without a same-day matching sell is a half-cycle and never counts; null dates are ignored entirely. Each day carries `by_etf` with per-code `rounds/t_net/n_buys/n_sells/buy_amount/sell_amount`; the day-level totals always equal the sum of the per-ETF buckets.
- `eod_report` embeds `summary`; a summary failure (OSError/ValueError) does NOT block the EOD report — it degrades to `summary=None` and the renderer prints ⚠️ and omits the T tables.
- `render_eod` emits: ⚠️ warning → 持仓概览 table → 累计做T table (+ bold totals row + “区间 start → end｜交易日 N 天｜净投入合计 X” line) → 当日做T table (+ totals row, or 当日无成交) → 剩余操作建议 → 来源 line.

## Iron rules

1. Every cell comes from the renderer output; the chat layer pastes it verbatim. No hand-typed numbers, no column the renderer does not emit (same rule as `entry_rank.render_markdown` for ranking tables).
2. Trading-day counts exclude A-share statutory holidays (weekends + the 2026 holiday set in `grid_summary.A_SHARE_HOLIDAYS_2026`); makeup Saturday workdays are not exchange trading days.
3. Script beats recollection: a hand-recalled aggregate that disagrees with the Decimal-summed script total is wrong (2026-10-26: recalled 2,720.00, script 2,720.20).
4. Half-cycles never count as rounds (2026-10-26 incident: hand-assembled “3 rounds/+349.20” was really 2 rounds/+233.60).

## Verification pattern

1. TDD first: `test_eod_table.py` (5 tests — tables present, summary embedded, empty day, by_etf bucket consistency, ETF rows + totals row). Fixture rule: build states with `confirmed_589720.build(inputs, code=..., name=...)` and inject dates into **trades only** — `validate_state` replays t_records and requires byte-identical match, so never hand-edit t_records or put dates there.
2. Focused suite: `pytest test_eod_table.py test_daily_rounds.py test_grid_summary.py test_grid_summary_edge.py test_confirmed_runtime.py test_eod_holdings_regression.py -q`.
3. Real-ledger preview: run the production wrapper `python "D:/Hermes Agent CN Desktop/data/hermes-home/scripts/grid_eod_decision.py"` and paste exactly what tomorrow's 15:20 push will contain — the run IS the deliverable, not a description of it.
4. Full-suite triage: classify failures (pre-existing subsystem / inter-test interference / real regression) before reporting; see the `research-system-health` skill.

Commits: a756048 (daily stats land on sell date), 7acdd20 (EOD tables), db87b13 (by_etf bucket + totals row).
