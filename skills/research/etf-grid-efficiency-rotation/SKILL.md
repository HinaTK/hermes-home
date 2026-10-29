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

### EOD push format: script-rendered tables (user rule 2026-10-26)

The 15:20 daily EOD push (cron b3097b45fafa → `grid_eod_decision.py` → `eod_main` → `render_eod`) must be markdown tables, not line-by-line prose: a 持仓概览 table (close/qty/sellable/max grid/net invested/T net/completed rounds); a 累计做T table (per-ETF rounds/gross/two-side fees/T net + bold totals row, plus window span, A-share trading-day count, and net-invested total); and a 当日做T table (per-ETF rows from `daily[asof]['by_etf']` + totals row, or 当日无成交 when the day has no fills). All cells come from the renderer over the `summary` that `eod_report` embeds from `grid_summary.summarize_account`; the chat layer pastes the rendered output verbatim — no hand-typed cells, no columns the renderer does not emit. Rounds key to the SELL trade's date; a same-day rebuy without a matching sell is a half-cycle and never counts. When a recalled aggregate disagrees with the script total, the script wins (2026-10-26: recalled 2,720.00 vs script Decimal sum 2,720.20 — memory corrected). Verify by running the production wrapper against the real ledger and pasting exactly what tomorrow's push will contain.

See `references/eod-daily-report-tables.md` for the schema, fixture rules, tests, and verification pattern.

## Weekly per-holding dual-track comparison (2026-10-11)

最新用户授权以逐持仓双轨替代旧全局589720门槛：159363与589720各自作为基准，159992保持exit-only。以下旧same-class与single-baseline段落仅作历史解释，不能据此继续用589720挡住替换159363的候选。实施与验证遵循 `references/per-holding-pair-review.md`；正式同类/跨题材信号只消费官方已核taxonomy，未知分类仅观察。新pair连续周不继承旧global streak，数据降级仍显示完整候选比较但不推进复核。

## Historical weekly same-class comparison

1. Freeze the portfolio baseline first. For the current authorized migration, 589720 is the innovation-drug baseline replacing 159992; 159992 remains exit-only.
2. **The candidate pool must include every live holding, not just same-class peers.** A hardcoded theme list that omits currently-held ETFs (e.g. 159363 创业板人工智能, 159992 创新药) silently drops them from the ranking and makes the report look as if they don't exist. Always maintain a `HOLDINGS` list — current positions that are fetched, simulated, and reported regardless of which theme bucket they fall into. Holdings are shown for reference and never trigger a switch review on their own.
3. Compare every eligible same-class candidate over the same trailing **63 confirmed sessions**, approximately three months. Preserve coverage, liquidity, exclusions, and failures; do not hand-pick a winner.
4. Use a fully specified executable model where available. A close-only 2% cycle proxy is acceptable for preliminary ranking only and must be labeled as a proxy: it does not establish intraday order, actual fills, T+1 availability, spread, slippage, or broker feasibility.
5. Persist weekly state by candidate, date, baseline, window, method, and errors.
6. Only if the **same candidate** beats the baseline in completed-cycle count in two consecutive weekly observations should the report say HUMAN_ROTATION_REVIEW. Otherwise report observation only.
7. Even after that threshold, require a human review of liquidity, bid-ask spread, fund operation, tracking error, shared-index correlation, shared cost cap, cash floor, fees, T+1, current quote timestamp, frozen cash, existing broker orders, and available shares.

## Unified research workflow (2026-10-10 user correction)

2026-10-10 用户明确要求统一研究链路：每次复用 research 重新筛选和排名，weekly 只调用其结果并维护连续周观察，不再独立维护日线排名或小主题池。以下表格描述的是旧实现，不能当作继续保留两套逻辑的理由。旧研究固定窗口必须先参数化并刷新数据，不能将旧缓存重跑称为最新排名。

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

**旧 weekly check uses the same 321-ETF eligibility pool as the full-market study** (`cache/grid-broad-20260923/eligibility.csv`). It re-fetches daily closes for all 321 and re-simulates the trailing 63 sessions every run. It is NOT limited to a 13-ETF theme list — that was a bug that silently dropped live holdings (159363, 159992) from the ranking.

统一后 research 是排名、模型和候选筛选的唯一来源；weekly 只负责调用最新研究结果、生成报告和维护连续周信号。不得维护独立 daily proxy 排名。旧表仅解释迁移前文件，不能据此声称新实现已部署或已完成最新全池验证。

旧固定窗口的 ranking-all-321.csv 只作历史参考。用户要求每次从全合格池用统一 research 流程更新数据并重排；运行成本可用增量缓存降低，不能因此继续另用 daily proxy 作为每周权威排名。尚未刷新或覆盖不足时应明确失败/缺失，不伪称最新全池结果。

## Unified implementation and verification

项目实现位于 `D:/Code/AH_analyse/tools/etf_research/`：research.py → engine.py（唯一5分钟模型排名），weekly.py 仅调用研究并报告/维护状态。三个旧入口 `scripts/grid_weekly_rotation.py`、`scripts/run_rotation.py`、`cache/grid-third-20260930/research.py` 应为薄 wrapper；`deploy_launchers.py` 先备份再替换，不能触碰账本/交易脚本。运行 `python -m pytest tools/etf_research -q` 并通过生产wrapper做真实数据验证。

默认池是2026-09-23的历史321只资格快照+持仓，不是实时上市全市场发现；默认滚动63日，实时刷新5分钟数据，共同窗口，费用万一最低1元。轮换按往返/净差价/周转；第三ETF互补视图用相关性门槛，同一套模拟供两视图，不把corr<0.8强加轮换。offline/smoke/历史日期/不同窗口或自定义池不得推进生产连续周或宣布复核门槛；失败与模型资格排除分开，覆盖变化重置。不要把资格快照全池尝试等同全部成功覆盖。

## Migration and authorization gates

Maintain three states separately: broker state, local state, and authorization state. A local exit-only guard does not prove a broker cancellation. A target appearing in a research report does not authorize a purchase. A threshold crossing means review is due, not that a switch or order is approved.

For a staged migration:

- source ETF: stop new buys and post-sale rebuys; preserve existing inventory for orderly exit;
- target ETF: remain research-only until old orders, fills/cancellations, frozen funds, available cash, quote timestamp, spread/premium/discount, and shared cost cap are reconciled;
- unaffected ETF: retain its existing policy;
- account capital, grid gap, per-name/group caps, lot budgets, and cash floor remain unchanged unless explicitly authorized.

## Pair comparison presentation (user correction)

When presenting same-class or cross-theme priority candidates, show each candidate **alongside its own holding baseline**, not candidate counts alone or a separate holdings section. Required row: route; holding code/name → candidate code/name; full-window completed cycles holding → candidate; signed absolute cycle gap; recent20 cycles holding → candidate; signed recent gap. Compute gaps from the exact saved run in code. State the shared window and simulation-vs-confirmed-fill basis. If recent counts tie, say so explicitly: midterm leadership is not recent cycle-count superiority. Priority also considers capital efficiency, so distinguish count leadership from satisfying the full rule. Include retained-holding overlap warnings and coverage/valid-week status; a large cross-theme cycle advantage does not itself justify concentrating the portfolio. The same comparison format belongs in both chat summaries and generated weekly reports; a report with numbers scattered across separate sections is not sufficient.

See `references/pair-comparison-reporting-and-validation.md` for the comparison template and taxonomy/state regression checks.

## Evidence and reporting

Separate actual realized P&L, mark-to-market inventory P&L, and proxy cycle counts. State whether the result uses confirmed fills, daily closes, or an executable simulation. Overlapping 63-session windows are correlated and are not independent trials. Historical leaders do not guarantee future turnover.

A report should include: baseline, candidates and exclusions, common window, method, completed-cycle counts, leader and count gap, consecutive-week state, data errors, path classification, downside/inventory interpretation, and the exact next review trigger.

**Cycle-count provenance (2026-10-24, sz159615 challenge).** A simulated cycle count can contain initial-inventory disposals: `recent20_sales=12, initial_sales=3` means only 9 of 12 sales were buy→sell T rounds, and a window that opens on a rebound inflates the count for a new entrant. When reporting a name's activity, either report pure-T cycles or state the initial-sale share; also state whether "20 日" means 20 trading sessions (yes) with the natural-day span when it exceeds a month. Verify a challenged number in three layers before defending or retracting: (1) re-run the module and compare with the delivered table, (2) independent market source for the bars, (3) `simulate(trace=True)` event log with `initial` flags.

## User workflow: recall, trend review, and implementation

- For any code change in this workflow, load and actually follow the Superpowers `systematic-debugging` and `test-driven-development` skills: reproduce the exact symptom, observe a targeted failing test, implement the minimal fix, and verify the deployed path. Do not claim TDD merely because existing tests pass.
- When asked whether unilateral rises/falls were discussed, search the specific topic in memory and original session history before answering. Do not substitute a general memory recap. An unsuccessful search is not evidence that the discussion never happened. Separate historical agreement from current implementation and current authorization.
- When a holding is revisited immediately after that discussion, evaluate inventory accumulation versus realized turnover. Refresh the persisted ledger and timestamped market data; distinguish narrow-range inactivity, upward sell-out/rebuy failure, and downward buys-without-exits. Do not veto a grid merely for unrealized losses or moving-average position. Missing historical fill dates prevent claims about recent actual cycle counts. Proposed pauses/rebasing are recommendations, not script changes or broker cancellations.
- Keep net cash invested, open-lot cost, realized T profit, and mark-to-market P&L distinct. If total P&L is market value minus cumulative net investment, do not add realized T profit again.

See `references/research-rerun-acceptance.md` for full-run acceptance and launch-path verification. See `references/weekly-report-entry-rank-integration.md` for the cron weekly-report ⇄ entry_rank integration and its iron rules. See `references/efficiency-metric-definitions.md` for the three efficiency metrics (per-round yield, capital turnover, engine cycle_net_per_avg_cost_pct), their different denominators, and the window-length/denominator normalization required before comparing ledger performance with engine simulation.

## Verification

When changing an existing monitoring workflow:

- write behavior tests for cycle counting, insufficient data, same-candidate consecutive-week persistence, same-day rerun idempotence, candidate changes resetting the streak, and migration precedence;
- run the focused tests and the existing grid regression suite;
- compile/run the production scripts;
- read back scheduled jobs and verify schedule, delivery target, enabled state, script, and workdir;
- never claim a cron `ok` proves Feishu delivery or broker execution.

See `references/rotation-efficiency-review.md` for thresholds, state fields, and a reusable implementation outline.

See `references/grid-crossings-and-trend.md` for the algorithm behind grid crossings and trend ratio, including why max/min range is misleading.

## Production scope isolation (critical pitfall)

The weekly report must never let a non-production run contaminate the production consecutive-week state. A run is **production scope** only when ALL of:

- online (not `--offline`),
- no `--limit` (full pool, not smoke),
- `sessions == 63`,
- `asof == latest_session()` (most recent closed session, not a historical date),
- eligibility CSV byte-identical to the default production snapshot.

Any run that fails any of these is **validation only**: it must not read the production state file, must not inherit an old streak, must not write the state file, and must not report `review_due=true`. The report must explicitly say it is validation-only.

**Coverage degradation must never be dressed up as success.** When some assets fail to simulate (data gaps, missing windows, model exclusions such as `initial orders exceed 1% first bar volume`), the report must state the exact successful/failed/excluded counts, the number of assets with complete four-window coverage, and that the result is degraded. A degraded result never advances the production consecutive-week counter and never triggers a rotation review — even if the same candidate appears to lead for two calendar weeks.

**Separate data failures from model exclusions.** Model exclusions (e.g. first-bar volume too small for the initial lot) are legitimate eligibility filters and may be counted under a *coverage signature* that allows consecutive-week accumulation when the same set of assets remains complete. Data failures (fetch errors, missing bars, stale endpoints, incomplete intraday coverage) break the signature and reset the streak. Never lump them together.

## Two views, one simulation

The ranking engine produces **one set of simulation runs** (full / early / late / recent20 windows). Two views consume it:

1. **Rotation view** — candidates with complete four-window coverage, non-holding, and `full_cycles` strictly greater than the baseline. Sorted by `full_cycles`, then `full_cycle_net`, then `full_cycle_net_per_avg_cost_pct`. **No correlation gate** — a rotation candidate does not need to be decorrelated from existing holdings.
2. **Complementary / third-ETF view** — same simulation, but scored with the original qualification gates (idle efficiency, worst-half efficiency, max correlation to base < 0.8, etc.). Holdings are shown but never scored or ranked as leaders.

The weekly report must show **both**: the rotation top-10 (with names) and the complementary top-10. Never present the complementary ranking as if it were the rotation ranking.

**Keep the universe count top-10 separate from the actionable rotation shortlist.** A baseline-beating shortlist may contain zero or fewer than ten rows; label its actual size and do not use it to populate or suppress the universe top-10. If `rotation_top10` is empty, read the saved complete-coverage ranking and sort by completed cycles to answer a count-ranking request; an empty filtered field does not mean count results are unavailable. Never silently substitute the complementary score list. See `references/count-ranking-delivery.md` for the extraction and reporting checks.

**When the user asks to re-run and see the result, actually execute it and paste the output.** Do not summarise what the output would look like and ask whether they want it run — the run is the deliverable. A `--asof` historical date is acceptable when the current session is outside trading hours; say so in one line and then show the full report text.

## On-demand top-10 delivery and ETF cost checks

When the user asks research to run and output the top ten, run the actual online research CLI and read that run's saved result; do not reuse an earlier background notification as a new run. Default to the latest closed session rather than hardcoding a historical asof. Extract only necessary columns from JSON/CSV, not ten full metric objects that flood the context. Count and sort programmatically.

Distinguish three lists explicitly: (1) research default complementary score top ten; (2) complete-coverage universe ranked by full_cycles, then full_cycle_net, including holdings for comparison; (3) rotation shortlist, which excludes holdings and only includes candidates beating baseline. The third may legitimately have fewer than ten rows; it is not the universe top ten. For this user's ETF grid research, an unqualified “排名前10 / 本次前10” defaults to the **completed-round-trip count ranking**, not the complementary score ranking. This preference was explicitly reinforced after repeated corrections. **Entry-eligibility gate (2026-10-23, missed twice before the user re-issued it): only 可建仓 (judge_entry verdict `full`, 可以整仓) and 试错建仓 (`probe_only`, 仅试错仓) names may enter the ranking; other timing verdicts are excluded.** **Holdings-merge rule (2026-10-23 session, then refined 2026-10-24): holdings are NOT blanket-excluded from the ranking. The 2026-10-23 user correction "不用排除持仓，我还是需要知道持仓排名第几的" means holdings stay in the SAME ranked table with their own rank position and a `持仓` tag — the user wants to know where his holdings rank. (2026-10-24's later refinement adds the gate: holdings passing full/probe_only merge labeled `持仓 · <verdict>`; holdings failing the gate list separately with reason + exit price.) Implementation commit `0176cb5` (TDD, test_entry_rank.py 3 tests RED→GREEN): `entry_rank.rank_entries` keeps holding rows in `rows`, labels them `持仓`, adds `holding` column to entry-ranking.csv, and `rank` is now in the row dicts. Sort remains full_cycles → full_cycle_net → efficiency → code over the merged table.** Run `python -m tools.etf_research.entry_rank <latest-run-dir>` instead of hand-filtering result.json: it reads the saved run, applies judge_entry on daily bars as of the run's asof, counts exclusions (holding/incomplete/timing/no_bars/error), sorts full_cycles → full_cycle_net → efficiency → code, and writes entry-ranking.csv. Deliver rank/code/name/资格/往返/净差价 with the admitted and excluded counts, and note that most high-cycle names sit low in downtrends so land 仅试错仓 (2026-10-23: 239 probe_only, 1 full). **Deliver ranking tables by pasting `--render` output** (render_markdown, commit f8e06b7, 2026-10-24): never hand-type cells, never add a column absent from the script output — 2026-10-24 the assistant hand-wrote a 近20日往返 column with numbers matching no field in the run's data (actual CSV: mostly 0) and the user escalated "一切数据都有依据" to a hard rule. See `references/entry-eligibility-ranking.md`. The holdings-included universe view remains a separate, clearly labeled comparison. See `references/entry-eligibility-ranking.md` and `references/entry-timing-vs-entry-rank.md` (verdict engine vs batch orchestrator division of labor, plus the 2026-10-23 logic audit: tests green, dual-path verdict agreement, four known conservative trade-offs), and `references/holdings-included-ranking.md` for the holdings-merge procedure and the recent20-vs-full-count activity divergence pitfall. **Additional gates added 2026-10-24 (user-approved, strict TDD): (a) close below ALL FIVE averages (ma5/10/20/30/60, break-count ≥5) → `no_entry`, no probe, no exit price — the old single-ma60 probe test is too loose; (b) candidates with recent20 completed cycles < 2 (exactly 2 passes; holdings exempt for visibility) are excluded — see `references/five-average-and-recent20-gates.md`.** **Weekly-report integration (2026-10-24, user: "这个定时任务我要求使用刚才的改动脚本去整改", commits 888a347/e9df0da): cron 5d8180a8d025's report now carries the dual-rule gated listing — block titled by the shared constant `weekly.ENTRY_BLOCK_TITLE`, table rendered ONLY by `entry_rank.render_markdown` (default top_n=20, "以后给出前20"), failures emit visible ⚠️ lines (never silent gaps), Feishu digest keeps 3 rows. When firing the cron on a non-trading day, the "休市不生成报告" reply is the production-scope guard working — to produce a report out-of-hours re-run `python -u -m tools.etf_research.weekly --asof <latest-closed-session>`. See `references/weekly-report-entry-rank-integration.md` for the four iron rules (shared-constant assertions, no second renderer, visible failures, weekend no-op) and the verification pattern.** State the universe, window, exclusions and tie-break rule. Do not answer with scores only, or merely append cycle counts to a score-ordered list. Show the complementary score list only when requested or as a clearly secondary view. Include code, name, 63-session cycles, simulated net spread, recent20 cycles; format currency to two decimals and scores to three. Mention data coverage and independent-account assumptions; never equate net grid spread with total account profit or actual fills.

For a mainland-listed ETF investing through Stock Connect, separate investor-level ETF share trading charges from fund-level underlying Hong Kong stock taxes and expenses. A name containing 港股通 does not mean the investor's ETF trade is a direct Hong Kong stock trade. Verify listing venue, current prospectus, broker tariff and relevant tax rules before asserting charges. Do not promise the user's existing ETF commission agreement applies to another instrument without broker confirmation; do not infer T+0/T+1 from its name. Underlying taxes and management/custody expenses affect NAV and should not be charged again to each simulated ETF share trade. See `references/top10-and-stock-connect-costs.md` for extraction and source-checking details.

## Filtered rankings and recommendation accountability

When the user temporarily excludes a category pending verification, apply it to the requested report only; do not silently change the production universe, cron, holdings, or trading authorization. State the exact exclusion: 港股通-only is not the same as all Hong Kong exposure. A name-based 港股/恒生/H股 screen is a disclosed preliminary proxy, not verified portfolio classification; do not expand the user's scope silently. Reuse the just-completed research run for a filter-only request and say this is re-filtering, not a fresh online run. Preserve the existing score ordering unless explicitly recomputing scores; sorting by cycles is a separately labeled view.

For “where do my holdings rank?”, use the exact same window, exclusion scope, completeness gates and sort order as the preceding table. Merge complete candidate rows with holdings, deduplicate by code, sort in code, and give all holdings' ordinal ranks with the eligible denominator. State the tie-break convention (cycles, then net spread; ordinal ranks need not be shared for equal cycle counts). Holdings excluded from complementary scores are not thereby low-ranked. Missing coverage means unranked, never bottom-ranked.

**Dual-window decision matrix (2026-10-26, commits 4ccf3ba→c87fbe9).** The four research windows are FOUR INDEPENDENTLY-ANCHORED simulations (each anchors its grid to its own window's first bar open), so early+late≠full and recent20>full is a legitimate inversion (159366: full=4, r20=7; 63-day grid anchored high in July, recent-20 grid anchored low in September). `full_cycles=0/None` means the window was never simulated (first-bar volume too small), not "zero cycles in 63 days" — never present those two as the same thing. render_markdown now carries a 判断 column (✅双高 / ⏳等信号 / ⚠️脉冲 / ❌死水): full-cycle line unchanged (≥10), but the recent-20 high/low line is **median_r20_threshold = the admitted pool's median recent20_cycles**, recomputed per run and printed in the header for audit. User correction embedded: the admission filter (recent20≥2) is his personal pass line, NOT an efficiency frontier — do not reuse a gate as a matrix line. Threshold is computed over the FULL admitted pool (not top-N); boundary-inclusive; empty pool falls back to the admission gate. When proposing such lines, never hand-estimate: show the pool's distribution and let the user pick. See `references/dual-window-matrix.md`.

**Two-gate-system overlap (2026-10-26 finding, merge NOT yet executed).** The daily 15:20 EOD `RegimeGate` (ADX≥25 且 -DI>+DI → 暂停该ETF新格买入, in `confirmed_runtime.py`, fail-open on missing data) and the entry_timing five-average gate (破线计数≥5 → 禁入) answer overlapping questions with different signals: ADX is a **momentum/strength** test, the five-average break-count is a **position/depth** test. Live 6-ETF measurement on 2026-10-26: 3/6 verdicts disagreed (e.g. sh589720 五线全破禁入 but ADX=17.3 地量磨底 → RegimeGate 放行). When the user asks whether the gates duplicate: the live-intercept function (RegimeGate on holdings) and the position-depth + exit-price function (entry_timing on candidates) are both necessary; the duplicated parts are the direction check and the dual data sources. Proposed-but-not-implemented consolidation: one `gate_check` with four levels (五线全破=禁入 / ADX≥25 且 60日线下=暂停买 / 破1-4线=试错仓+20日最低退出价 / 均线上方=正常), strictest-wins, single data source. Do NOT present this as deployed — it was a discussion-stage proposal pending user approval.

For “why did you recommend this when it ranks poorly?”, retrieve the original dated recommendation/report before explaining. Lead with the documented reason, not a reconstructed narrative. Separate (a) what was known at recommendation time, (b) what changed in window/model/fees/coverage, and (c) failures in research or ongoing monitoring. Historical cycle counts alone do not establish historical rank; do not assert a rank without the original ranked universe. A current low rank does not prove the original recommendation was irrational, but window differences are not an excuse for stale monitoring. Acknowledge evidence limitations and process responsibility specifically, without claiming an untested replacement is optimal. Incomplete issuer diligence is a reason to finish diligence, not evidence that another ETF is economically superior. Keep the answer focused on the user's actual objective: net spread and capital turnover, not defending a favored theme or mechanically prioritizing short-term unrealized loss. No automatic liquidation or rotation follows from one ranking.

See `references/filtered-rankings-and-recommendation-audit.md` for extraction checks and the dated original-report evidence pattern.

## Implementation reference

The unified production implementation lives in `D:/Code/AH_analyse/tools/etf_research/`:

- `research.py` — public entry: `run_research()`, `main()`, `BASE`, `HOLDINGS`, `VERSION`, `load_universe()`, `select_window()`, `latest_session()`.
- `engine.py` — the only simulation pipeline: fetch (Sina 5m), validate, select common window, run `grid_model.simulate()` on four windows, build metrics, write JSON/CSV. Key outputs: `rotation_top10`, `rotation_ranking`, `ranking`, `holdings`, `summary` (with `production_pool`, `production_scope`, `latest_claim`, `rankable_rows`, `successful_assets`, `failed_assets`, `data_failed_runs`, `model_excluded_runs`).
- `grid_model.py` — copied verbatim from the original 104-session study; the **only** change is `fee()` minimum 5元 → 1元.
- `calendar.py` — verified 2026 SSE closures; fails closed for 2027.
- `weekly.py` — orchestrator only: calls `research.run_research()` once, maintains the versioned consecutive-week state, renders the Chinese report. Never simulates or ranks independently.
- `deploy_launchers.py` — replaces the three legacy entry points with thin wrappers; backs up originals first; never touches the ledger or trading scripts.
- `launchers/grid_weekly_rotation.py`, `launchers/run_rotation.py`, `launchers/research.py` — thin compatibility wrappers.

Tests in `tools/etf_research/test_research.py` and `test_entrypoints.py` cover: universe inclusion of all eligible + all holdings, weekend/holiday date resolution, common-window staleness/insufficiency, missing baseline sessions, model fee and constraints, four-window simulation, failure accounting, legal JSON (no NaN/Infinity), weekly single-call idempotence, versioned streak with coverage-signature reset, production-scope isolation (offline/smoke/historical dates/custom pools never inherit or trigger review), and launcher delegation without a second model.

The legacy `scripts/grid_rotation_review.py` (daily-close proxy, `simulate_daily_grid()`, `count_grid_crossings`, `recent_trend_ratio`, `assess_low_efficiency`) remains in place for the **daily** after-close efficiency review only. It is not part of the weekly rotation pipeline and must not be confused with it.
