# EOD table rendering (15:20 push, 2026-10-26 user rule)

User rule: the 15:20 daily push must be TABLES — total T stats and today's T stats, both script-produced. Line-per-ETF text was rejected.

## Data chain

- `confirmed_runtime.eod_report(root, now, quotes, bars)` embeds `summary = grid_summary.summarize_account(root)` (same root re-read). OSError/ValueError → `summary=None` — EOD is NEVER blocked by a summary failure; `render_eod` labels "汇总数据不可用" instead.
- `render_eod(report)` renders four sections, every number pulled from `report['summary']` / `report['decisions']`: no hand-assembled values anywhere.
  1. 持仓概览: close/qty/sellable/max_grid/net_invested/t_net/rounds per ETF.
  2. 累计做T: per-ETF t_rounds/t_gross/t_fees/t_net + bold 合计 row + 区间 start→end / trading_days / net_invested line.
  3. 当日做T（asof）: one row per ETF from `summary['daily'][asof]['by_etf']` + bold 合计 row; "当日无成交" when the day has no dated trades.
  4. 剩余操作建议: plan() actions verbatim.

## daily by_etf bucket semantics

- Rounds land on the SELL trade's date (round completes at the sell). Rebuys and any half-cycles NEVER count. Null dates are skipped.
- `by_etf[code]` carries rounds/t_net/n_buys/n_sells/buy_amount/sell_amount per code per day; the sum of per-ETF buckets MUST equal the day totals — enforced by test (prevents the summary table and the daily table from drifting apart).

## Test-fixture pitfall (validate_state replay)

`eod_report → plan → load_states → validate_state` REPLAYS trades through `confirmed_589720.build()` and requires saved `t_records` to byte-identical to the replay. Therefore in fixtures:
- Generate trades via `build(inputs)`; inject `date` ONLY into `trades` entries (validate ignores it), never into `t_records`.
- Hand-written t_records dicts fail with `经济周期成交ID链接不一致` even when every economic field matches.
- Every code's sub-ledger needs `sellable_qty` initialized (`state['sellable_qty'] = state['qty'] if state['qty'] else 0`) or plan() raises 保存的可卖库存无效.

## Commits

- `7acdd20` — eod_report embeds summary + render_eod tables (3 RED tests first).
- `db87b13` — daily by_etf bucket + per-ETF daily rows with totals (2 more tests).
