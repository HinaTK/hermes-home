# entry_timing vs entry_rank — division of labor & audit notes (2026-10-23)

## Division of labor

- `entry_timing.py` = **verdict engine** (single name). `judge_entry(frame, asof)` classifies one ETF's daily-bar position into: `reject` 否决建仓 (above all MAs and within 3% of prior 20d high — chasing), `no_entry` 不能建仓 (above MA20 without a ≤3-session pullback touch or >2 ATR extension), `probe_only` 仅试错仓 (close below MA60, exit = close through 20-session low), `full` 可以整仓 (≥3 consecutive closes above a non-falling MA60 + 3-session pullback to MA20 that holds), `wait` 等待触发, `insufficient` 数据不足 (<65 rows). Standalone CLI: `python -m tools.etf_research.entry_timing 159363 --asof YYYY-MM-DD` (Sina daily, unadjusted) or `--csv`.
- `entry_rank.py` = **batch orchestrator**. Reads a research run dir, drops holdings and incomplete-four-window rows, aggregates m5 bars → daily, calls `judge_entry` per name at the run's `asof`, keeps only `full`/`probe_only`, sorts full_cycles → net → efficiency → code, writes `entry-ranking.csv`. It has called judge_entry since its first commit (10-21, `10d479d`); when a top-10 was delivered without the gate, the failure was the agent hand-filtering result.json instead of running the existing module — not missing code.

## Audit of entry_timing logic (2026-10-23, user asked "逻辑是否存在问题")

13 unit tests pass; m5-aggregated-daily and standalone Sina-daily paths give identical verdicts for sh588010@2026-10-23 (probe_only, exit 0.762). No bugs found. Known design trade-offs / boundaries to disclose when asked:

1. **No full channel for a strong never-pullback name**: the only `full` path requires a ≤3-session MA20 pullback; a steadily rising ETF that never touches MA20 stays `wait` forever. Intentional conservatism vs defect is a user decision.
2. **Below MA60 is always probe_only** even if MA60 is still rising; a first shallow break and a -30% deep decline are not distinguished.
3. `recent_touch` window is 3 sessions — a pullback then a day-4 breakout can be missed for one session (re-evaluated next bar). Acceptable one-day lag.
4. **Data sources differ**: entry_rank uses research-cache m5→daily (unadjusted); standalone uses Sina daily (unadjusted). Distributions/splits distort MAs either way — flag for QDII names with dividends.

Deliver these as "conservative trade-offs, not bugs" with the evidence (tests green, dual-path agreement) and offer the user the decision on relaxing #1/#2 via Superpowers TDD.
