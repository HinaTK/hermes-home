# Filtered rankings and retrospective recommendation audit

## Deterministic report checks
- Read the saved result from the immediately preceding research run, including summary window and coverage counts.
- Freeze the requested exclusion scope. A literal name filter is a proxy: do not call it a verified all-A-share classification. If excluding all Hong Kong exposure rather than only names containing 港股通, disclose that distinction before presenting results.
- Filter only complete four-window rows for cycle rankings. Merge holdings, deduplicate code, sort by full_cycles descending and full_cycle_net descending, enumerate ordinal ranks, and compute the denominator programmatically.
- Extract small column sets only: rank, code, name, cycles, net spread, recent20 cycles. Format money to two decimals.
- A filter-only response is not a new data fetch. Do not write production state or persist exclusions without authorization.
- Distinguish original composite-score ordering from recalculating percentiles within a smaller universe. Removing rows from a score table does not recalculate its score.

## Historical rationale evidence
For recommendation challenges, first search conversation history; if it is dominated by compaction summaries, inspect the dated primary research artifact instead. Quote documented reasons and model settings, not a plausible story inferred from holdings.

Worked evidence from this session: original artifact `cache/grid-broad-20260923/扩大范围分钟网格研究-20260923.md`, dated 2026-09-23, data through 2026-09-22. The 104-session window was 2026-04-24→2026-09-22. Its 2% model with minimum 5元 commission recorded 159363 at 53 cycles / roughly 5,675元 spread and 159992 at 39 cycles / roughly 4,219元. These are documented simulation metrics, NOT proof of a particular historical rank. Reasons recorded: 159363 had better same-index liquidity than 159382; 159992 was described as more balanced in turnover/inventory. 589720's uncompleted issuer checks and weaker size/liquidity were cited as exclusions, but unfinished diligence is not evidence of worse grid efficiency.

The later rolling 63-session run with minimum 1元 and stricter coverage is not directly comparable. A fair explanation names these differences, then separately acknowledges that stale research plus a separate daily-proxy weekly model failed to provide consistent continuing opportunity-cost review. Avoid claiming that model changes alone caused deterioration unless a controlled rerun isolates that effect.

## Response structure
1. Answer the documented original reason directly.
2. Give only essential old-window metrics and assumptions.
3. Explain why present rank cannot be backdated.
4. Acknowledge specific evidence/monitoring failures.
5. State what current evidence does and does not justify; no automatic switch, no hindsight claim of an optimal replacement.

This reference is historical audit evidence, not a current recommendation or a perpetual exclusion policy.
