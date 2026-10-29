# Weekly report ⇄ entry_rank integration (cron 5d8180a8d025)

2026-10-24 整改：每周五 15:25 的定时任务（网格每周统一research重排与轮换复核，script `grid_weekly_rotation.py` → `weekly.py`）必须输出双规则可建仓榜单。Commits `888a347`（integration + failure visibility + push digest）、`e9df0da`（top_n 10→20）。

## What the weekly report now contains

- Block titled by the **shared constant** `weekly.ENTRY_BLOCK_TITLE` = '【可建仓候选·双规则过滤（五线全破禁入+近20日往返<2出榜，持仓豁免）】'.
- Header line: `asof … 入选 N 只；排除：时点禁入X、近20日不足Y、四窗口不全Z` (counts from rank_entries' excluded dict).
- Table: rendered by `entry_rank.render_markdown(report, top_n=20)` ONLY — there is no second hand-written renderer inside weekly.py. Default top_n is 20 (user 2026-10-24: "以后给出前20", commit e9df0da); every cell comes from rows verbatim (table-delivery iron rule).
- Feishu push digest (`summarize`, what cron actually delivers) carries `digest_n=3` rows + the counts line; the full 20-row table stays in `weekly-report.txt` and `entry-ranking.csv`. Do not inflate the push digest — long pushes get truncated.

## Four iron rules that came out of this integration

1. **Assert against the shared constant.** The 2026-10-24 false-negative: the integration test asserted a hand-typed substring `'【可建仓候选·双规则过滤】'` while the implementation header carried the parenthesized suffix — a PASSING feature was misdiagnosed as missing, triggering a long pointless debug chase (isolated duplicate test file passed, in-suite test failed). Fix: `ENTRY_BLOCK_TITLE` is one constant in weekly.py; report, digest and ALL test assertions reference it. Never hand-type the expected block header in a test.
2. **No second renderer.** The weekly table is `render_markdown` output pasted as-is. Any second formatting path re-introduces the hand-written-number class of error.
3. **Failures are visible, never silent.** The first `entry_rank_lines` had a bare `except Exception: return []` — a corrupt result.json produced a report with NO block and NO warning, indistinguishable from "no candidates". Now every failure path emits a `⚠️` line inside the block (no output_path / rank_entries exception). A silent gap in a scheduled report is a bug even when the rest of the report looks fine.
4. **Weekend/holiday runs correctly do nothing.** Manually firing the cron on a Saturday prints `周度研究：休市或收盘未确认，不生成报告、不更新状态。` — that is the production-scope anti-pollution guard working, NOT a failure. To produce a report outside trading hours, re-run the module with the latest closed session: `python -u -m tools.etf_research.weekly --asof 2026-10-23` (say so in one line when you do). Full-pool run ≈ 55s.

## Verification pattern after touching this pipeline

1. Full suite: `python -m pytest tools/etf_research -p no:cacheprovider -q` (95/95 as of e9df0da).
2. Real-data cross-check: the weekly run's `entry-ranking.csv` must be byte-identical to a standalone `python -m tools.etf_research.entry_rank <same-run-dir>` output (validated on 20261024-120136-571609 vs 20261023-170032).
3. Render check: the weekly report block's rows must equal `--render` output rows for the same run (no divergence between push digest, report table, and CLI).
4. Read back the cron job (cronjob list) to confirm schedule/delivery/enabled unchanged after code edits.

## Delivery deltas the user reads

When a gate or default changes, report the before/after admitted count and the movement of the user's holdings (e.g. top_n 10→20: rows 11–20 are the new content; the three holdings sit at ranks 1/4/8 on 2026-10-23 data). The user reads the delta, not just the new table.

Note: the standalone CLI `entry_rank --render` still defaults to top_n=10 — only weekly's block defaults to 20. If the user asks for a different N anywhere, pass it explicitly; do not retype the table with a different row count by hand.
