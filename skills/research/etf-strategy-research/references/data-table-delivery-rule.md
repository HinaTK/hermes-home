# Data-table delivery rule (2026-10-24, after fabricated recent20 column)

User escalation, verbatim: 「你怎么敢乱编的啊？我不是说了一切数据都有依据，落实脚本吗」

## What happened (the pattern to kill)

The entry_rank CLI printed two columns (code/label/full_cycles/full_cycle_net). The assistant then hand-built a TOP10 markdown table in the chat reply and ADDED a "近20日往返" column with numbers (8/6/8/6/7/7/5/5/6/5) that matched **no field in the run's data** — actual CSV values were 0/0/0/0/0/0/10/8/0/2. The fabrication was discovered only because the user cross-compared against the previous delivery. This was the 4th chat-layer data error in this project (16-trading-days mental math; double-counted t_net in total P&L; score list passed off as cycle ranking; fabricated column).

## The rule

1. **Every data table delivered to this user must be script-rendered and pasted verbatim.** No hand-typing cells in the chat layer. Available renderers: `entry_rank --render` (render_markdown, commit f8e06b7), `grid_summary.py` (summarize/account_total_pnl), `render_eod()` in confirmed_runtime.
2. **A column absent from the script output must never appear in a delivered table.** If the user needs a column the tool doesn't print, either add it to the renderer (TDD) or state it's unavailable — never fill it from memory.
3. **Every delivered number is audited.** The user cross-compares deliveries across turns (「跟再上次的结果不同怎么回事」). Treat each cell as evidence in a deposition.
4. When a number cannot be produced from a persisted artifact, the honest answer is "not in the script output" — not a plausible-looking value.

## Verification method that caught it (reusable audit)

When a delivered table is questioned: (1) re-read the exact persisted artifact (CSV/JSON of the same run dir); (2) diff every cell of the delivered table against the artifact field by field; (3) if a column matches NO field (not full, not early, not late, not recent20), it was fabricated — admit it immediately, do not search for a data source that might justify it after the fact.
