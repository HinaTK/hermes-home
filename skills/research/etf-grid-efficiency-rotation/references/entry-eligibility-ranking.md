# Entry-eligibility ranking (可建仓/试错建仓 gate)

## Rule (user, 2026-10-23)

“需要满足可建仓/试错建仓的才能进入排名” — a ranking of buy candidates may only contain names whose current price/position qualifies for building a position. This was missed twice before the user re-issued it; treat it as a standing gate on every "前10 / 排名" delivery of entry candidates.

**Holdings visibility rule (2026-10-23, "不用排除持仓，我还是需要知道持仓排名第几的")**: the ranking does NOT drop holdings — the user always wants to know what rank his holdings hold. In the 2026-10-23 session the first entry_rank patch (commit 0176cb5, TDD test_entry_rank.py 3 RED→GREEN) removed the blanket holding-exclusion entirely: holdings stay in the same sorted table, label `持仓`, `holding` column in entry-ranking.csv, `rank` added to row dicts. The 2026-10-24 follow-up (next session) layered the eligibility gate back on top for candidates only, keeping holdings visible even when they fail the gate (listed separately with reason + exit price). Both rules coexist: holdings always visible with rank; candidates gated by full/probe_only + recent20.

**Two further gates added 2026-10-24 (each TDD'd, user-approved):**

1. **All-five-averages break → 禁入 (no_entry).** `entry_timing.judge_entry`: when the close is below ma5/ma10/ma20/ma30/ma60 ALL FIVE (break-count ≥5), verdict is `no_entry` — NO probe position, and no exit price (no position → no exit line). The reason must state waiting for a close back above ma5. Break-count 1–4 keeps the original probe_only + 20-session-low exit line. Why: the user challenged "只判断一条日线就行了？" after sz159615 (five lines all broken, single-way slide) still got probe_only from a single ma60 test. Measured on the 2026-10-23 pool: of 242 names below ma60, 138 (57%) fell into the new no_entry class, dropping entry_rank admissions 243 → 105.
2. **recent20 completed round trips < 2 → candidate excluded (holdings exempt).** `entry_rank.MIN_RECENT20_CYCLES = 2`; candidates with 0 or 1 trailing-20-session cycles leave the table (new `recent20` exclusion counter). Exactly 2 stays (the rule is "少于2不含2"). Holdings are exempt so a dead-water holding stays visible for its rank and exit line — visibility, not endorsement. Combined effect on the same run: 105 → 38 admitted, and sh589720 (12 recent20) took rank 1 while the old full-count leaders (sh588010, 科创100 series, all recent20=0) correctly dropped out.

When a rule gate is changed, report the before/after admitted count and the movement of the user's holdings — the user reads the delta, not just the new table.

## Verdicts (`tools/etf_research/entry_timing.judge_entry`)

- `full` → 可以整仓 (可建仓)
- `probe_only` → 仅试错仓 (试错建仓)
- `no_entry` → 不能建仓/禁入 (added 2026-10-23 five-average rule)
- any other verdict → excluded (not an entry candidate)
- Holdings: NOT blanket-excluded (2026-10-24 user correction "我有说过我持仓也要参与排名吧？只要符合可建仓条件"). Run judge_entry on each holding too; holdings passing the same gate (full or probe_only) merge into the SAME ranking table labeled `持仓 · <verdict>`, sorted by the identical full_cycles → full_cycle_net → code rule using the same run's result.json holdings rows. Holdings failing the gate list separately with reason + exit price. See `references/holdings-included-ranking.md`.
- **Verdicts are date-stale — re-run per delivery** (2026-10-26): sz159363 was probe_only (break-count 1) at asof 10-23 and no_entry (five lines all broken, close 0.983 vs ma5 1.003) three sessions later. A verdict quoted from an old run is not the current verdict; always `python -m tools.etf_research.entry_timing <code> --asof <latest closed session>` before asserting a holding's current eligibility.

## Tool: `tools/etf_research/entry_rank.py`

```
cd D:/Code/AH_analyse && python -m tools.etf_research.entry_rank <research-output-dir>
```

- Reads `<dir>/result.json` (latest run dir under cache/grid-research; same-day multiple runs → latest timestamp).
- Groups the saved m5 bars into daily bars, judges entry at `summary['asof']`.
- Exclusion counters: `holding`, `incomplete` (missing four windows), `no_bars`, `error`, `timing`, `recent20` (recent20_cycles < MIN_RECENT20_CYCLES, candidates only).
- Sort: full_cycles desc → full_cycle_net desc → full_cycle_net_per_avg_cost_pct desc → code asc.
- Writes `entry-ranking.csv`; prints top 20 with verdict labels and the admitted/excluded line.
- `--render` flag (commit f8e06b7, 2026-10-24): `render_markdown(report, top_n)` emits a paste-ready markdown table where EVERY cell is formatted directly from `report['rows']` fields — no chat-layer retyping. This exists because the assistant once hand-wrote a "近20日往返" column in a delivered TOP10 whose numbers (8/6/8/6/7/7/5/5/6/5) matched no field in the run's data (actual: 0/0/0/0/0/0/10/8/0/2). The user's standing rule: 一切数据都要有依据. DELIVER RANKING TABLES BY PASTING `--render` OUTPUT — never hand-type cells, never add columns absent from the script output. Note the CLI `--render` still defaults to top_n=10 while the weekly-report block defaults to 20 (user 2026-10-24: "以后给出前20", commit e9df0da); when a different N is wanted anywhere, pass it explicitly rather than retyping rows by hand.

## Delivery format (validated on the 2026-10-23 17:00 run)

- Preferred: `python -m tools.etf_research.entry_rank <dir> --render` and paste verbatim. Columns: 名次/代码/名称/资格/63日往返/净差价/近20日往返/资金效率%.
- State admitted/excluded counts and that timing verdicts come from judge_entry on daily bars as of the run's asof.
- Worth stating: high-cycle names usually sit low in a downtrend → nearly all land 仅试错仓; 可以整仓 names are trend-up names with fewer cycles (2026-10-23: 239 probe_only vs 1 full — sz159981, 8 cycles, rank 139). This is consistent with the market-phase ladder (单边下跌 → 试仓 1 成).
- recent20_cycles=0 rows are real signal, not missing data: names whose full_cycles were all earned in an earlier downtrend with zero completed round trips in the trailing 20 sessions (grid can't sell in a one-way slide). Cross-check recent20 before praising a high-cycle name.
- "Recent 20 days" means 20 TRADING sessions, not natural days — the 2026-10-23 window 2026-09-18 → 2026-10-23 spans 36 natural days and 16 non-sessions (weekends + 中秋 9-25 + 国庆 10-01–10-07). When reporting a window, give the trading-session count and, when the span is long, name the holidays; a user reading "20日" may reasonably assume calendar days.
- When a delivered number is challenged, verify in three layers before defending or retracting: (a) script output vs rendered table, (b) two independent market sources for the underlying bars, (c) the simulation's own event log (re-run `simulate(trace=True)` and print buy/sell events). For sz159615 this proved the 9 cycles were real BUT included 3 initial-inventory sales (recent20_sales=12, initial_sales=3) — the honest number was 7 pure T cycles, and the window opened on a +6.7% rebound before the October slide. Verification that ends at "the CSV says so" is incomplete.
- Simulations start each window by building core + grid inventory at the window open, so early window sales include initial-inventory disposals. A high cycle count anchored to a rebound at the window start overstates what a NEW entrant could have earned. Say so when the cycles cluster near the window start.

## Pitfalls

- Do not hand-filter result.json when entry_rank.py exists (user's code-first rule).
- Do not hand-write table cells in the chat reply — paste `--render` output. A column absent from script output must never appear in a delivered table.
- Entry-eligibility gates candidate-ranking display only; the rotation consecutive-week state still uses its own production-scope rules. A probe_only label does not pause an already-held grid.
- Re-run entry_rank on the latest run dir — timing verdicts go stale as price moves.
- Test-fixture pitfall seen here: a list comprehension referencing an outer-loop variable (`holding=code in holdings` where `code` leaked from a previous loop) silently marked every row as holding. In fixtures, always use the comprehension's own loop variable explicitly.
