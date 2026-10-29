# Holdings-included entry ranking (2026-10-24 correction)

User correction, verbatim: "我有说过我持仓也要参与排名吧？只要符合可建仓条件" — holdings participate in the SAME ranking as long as they satisfy the entry-eligibility gate. The prior default (holdings shown only in a separate reference block, excluded from the entry ranking) was wrong for this user.

## Procedure (all in code, same saved run)

1. Run `python -m tools.etf_research.entry_rank <latest-run-dir>` → ~240 admitted rows in `entry-ranking.csv`.
2. The module already merges holdings into the ranked output (label `持仓`, verdict from judge_entry run per holding; holdings failing the gate are listed separately with reason + exit price).
3. Pull each holding's simulated row from the SAME run's `result.json` `holdings` dict (same window, same model — do not re-simulate or use another run).
4. Sort: `full_cycles` desc → `full_cycle_net` desc → code asc (identical tie-break for holdings and candidates).
5. Deliver via `--render` (render_markdown): rank / code / name / 资格 / 63日往返 / 净差价 / 近20日往返 / 资金效率%, plus admitted+excluded counts and the usual 口径声明 (lot 5000 / 2% gap ≠ live params, independent 100k simulated account, coverage degradation).

## Why the exit price matters for holdings

For an already-held ETF the judge_entry verdict is not a buy/no-buy signal — it is a thesis line: `收盘跌破近20日最低X退出` gives a concrete invalidation price that triggers BEFORE a 25%-style stop. Report it next to every holding row.

## Pitfall: recent20 activity vs full-window count

High full_cycles with recent20 = 0 means the count was earned in an old downswing and the name is currently dead water (2026-10-23: the top-6 by full count all had recent20 = 0, while sh589720 held #7 overall with 12 recent20 cycles — best in the whole pool). When the user's core metric is sustained completed round trips, surface recent20 alongside the rank, and call out this divergence explicitly rather than letting the full-window count imply current activity.

## History of this rule (do not regress)

- First the assistant hand-merged holdings in a throwaway script (10-24 morning) — worked but untracked.
- entry_rank was then updated in-repo: holdings keep `label='持仓'`, are ranked with the same sort, and `render_markdown` (commit f8e06b7) renders them with a per-holding verdict. A fixture bug was fixed in the same commit: the make_output comprehension leaked an outer-loop `code` variable, silently marking every row `holding=True` — in fixtures always use the comprehension's own loop variable explicitly.
