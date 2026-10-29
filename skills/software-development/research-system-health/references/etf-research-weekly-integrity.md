# ETF research weekly chain integrity (AH_analyse/tools/etf_research)

Repair record 2026-10-24, commit `888a347`. Class of problem: scheduled
research/reporting pipelines whose output reaches the user through a
DIFFERENT surface than the one you fixed.

## Delivery-surface rule

Cron `5d8180a8d025` (Friday 15:25) runs `scripts/grid_weekly_rotation.py`
→ `tools.etf_research.weekly:main`, but the Feishu push is the `summarize()`
DIGEST, not weekly-report.txt. A fix that only lands in the full report is
invisible in the user's push. When repairing the chain, first establish
which surface the cron actually delivers (`grep` the script's stdout path)
and fix THAT surface.

## Single-renderer rule (user mandate)

Every delivered data table is rendered by exactly one canonical renderer
and pasted verbatim. For the entry ranking that is
`entry_rank.render_markdown` (commit f8e06b7). `weekly.py` must not grow a
second hand-written formatter for the same rows — the 2026-10-23
fabricated-column incident (4th of its kind) came from re-typing table
cells at the chat layer. The push digest follows the same rule: digest
lines are generated from `rank_entries` rows in code, never typed.

## No silent report gaps

`except Exception: return []` in report generation turns real failures
into a quietly missing block. Both the weekly report AND the digest must
carry a visible ⚠️ line naming the failure. "入选 0 只" is also a visible
state with its own explanatory line, never a skip.

## Misdiagnosis postmortem (assertion-literal drift)

The 2026-10-23 session ended believing "same code passes in an isolated
pytest file but fails inside test_research.py → test-order state
pollution". Wrong. The feature worked all along; the integration test
asserted a hand-written header literal `【...双规则过滤】` while the code
emitted `【...双规则过滤（五线全破禁入+近20日往返<2出榜，持仓豁免）】`
— the assertion could never match, in any file, in any order. A wrong
root-cause guess written into a session handoff then survived into the
next session as "known cause".

Lessons for any pipeline test repair:
- When the failure is `assert X in <generated output>`, PRINT the actual
generated value first (`pytest -s` — plain runs capture stdout and hide
the evidence) and diff it against the asserted literal before forming
any environmental theory (state pollution, import shadowing, cwd).
- Assert against a constant the implementation defines
  (`weekly.ENTRY_BLOCK_TITLE`), never a second hand-written copy of the
  string. Two copies WILL drift apart.
- Re-verify any root-cause hypothesis inherited from a handoff/summary
  from fresh evidence — a written-down guess is not a finding.
- A bare `except Exception` near the suspect code can swallow the real
  error and steer the whole investigation wrong; instrument past it.

## Real-data validation recipe (no research re-run)

To validate a reporting-chain change against production output without
re-running the ~15-minute research:

1. Create a throwaway dir under `cache/grid-research/`; copy `result.json`
   (and any CSV to byte-compare, renamed e.g. `entry-ranking.old.csv`).
2. Link bars read-only via Windows junction:
   `python -c "import _winapi; _winapi.CreateJunction(src_bars, dst_bars)"`
   — 95MB / 321 files cost zero copy time. Remove with `rmdir` on the
   junction ONLY; a recursive delete destroys the production bars.
3. Custom runner returns the real result with `summary.output_path`
   pointed at the throwaway dir; call
   `weekly.run_weekly(state_path=<throwaway>, pair_state_path=<throwaway>)`
   so production rotation/pair state is never touched.
4. Byte-compare the freshly written `entry-ranking.csv` against the
   `.old.csv` — the integrated path must reproduce the standalone run
   exactly (`new == old: True`).
5. Total cost ~8s. Delete the throwaway dir afterwards.

## Chain map (as of 888a347)

```
cron 5d8180a8d025 → scripts/grid_weekly_rotation.py → weekly.main
  → engine.run_research (writes result.json, ranking.csv, bars/)
  → pair_review.run_pair_review
  → entry_rank.rank_entries(result.json + bars/*-m5.csv) → render_markdown
  → weekly-report.txt (full report, stays on disk)
  → summarize() digest (what Feishu actually receives)
```

State guardrails: production streak state lives at
`cache/grid-account/rotation/<STATE_VERSION>.json`; validation runs must
always pass custom `state_path`/`pair_state_path` so consecutive-week
streaks are never advanced or rewound by a test.
