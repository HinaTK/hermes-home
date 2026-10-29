# Five-average break rule and recent20 floor (2026-10-24)

Two user-approved gates added to the entry pipeline after a challenge to the probe-only logic. Both were implemented strict-TDD (RED → GREEN → full suite) in `tools/etf_research/`.

## Gate 1 — all five averages broken → no_entry

- Implementation: `entry_timing.judge_entry`, inside the `close < ma60` branch:
  ```python
  below_count = sum(1 for period in (5, 10, 20, 30, 60) if close < ma[period])
  if below_count >= 5:
      verdict = 'no_entry'   # reasons: list all five MAs + "禁入：等收盘先站回5日线X上方再重新评估"
      exit_price = None
  else:
      probe_only + exit at 20-session low   # reasons now include "破线计数N/5，未全破"
  ```
- Commit `4e0ffcb`. Tests: new `test_close_below_all_five_averages_is_no_entry`, `test_partially_broken_averages_still_probe`, `test_decline_with_recent_bounce_under_60_day_is_a_probe`. One pre-existing test (`..._is_a_probe_even_while_still_falling`, built on a single-way 80-day slide) was UPDATED to expect `no_entry` — a sustained slide below every average is exactly the new banned shape. Suite 88/88.
- Pool effect: 242 names below ma60 → 138 (57%) no_entry; entry_rank admissions 243 → 105.
- Why a count, not a combination table: with ordered MAs the break patterns are not free combinations — measured distribution of (ma5,ma10,ma20,ma30) breaks among the 242: (1,1,1,1)=57%, (0,1,1,1)=23.6%, (0,0,1,1)=14.9%, everything else ≤2.4%. "Count ≥5" is the simple equivalent of enumerating shapes and cannot fragment.

## Gate 2 — recent20 < 2 completed cycles → candidate excluded

- Implementation: `entry_rank.MIN_RECENT20_CYCLES = 2`; after the timing gate, candidates with `(row['recent20_cycles'] or 0) < 2` and not a holding increment `excluded['recent20']` and skip. Exactly 2 passes ("少于2不含2"). Commit `f2266ef`. Suite 91/91.
- Holdings are exempt on purpose: the user wants to see where a dead-water holding ranks (159363 recent20=0 stayed at rank 4 on 2026-10-23) — the exemption is for visibility and exit-line reporting, NOT an endorsement to add.
- Pool effect: 105 → 38 admitted. sh589720 became rank 1 (12 recent20, also best-in-pool); the old full-count leaders (sh588010 37 cycles, 科创100 series) dropped out with recent20=0.

## Re-running with the new gates

```bash
cd D:/Code/AH_analyse && python -m tools.etf_research.entry_rank <latest-run-dir> --render
```

Same saved run re-judged (no re-simulation needed) — gates are daily-bar position rules evaluated at the run's asof. Deliver the admitted/excluded delta versus the previous rules so the user sees what the new gates removed.

## Verification pattern when a ranking number is challenged

1. Re-run the module (`--render`) — script output vs the delivered table.
2. Independent market source for the bars (Sina daily vs the cached m5) — full OHLC agreement, not just the close.
3. Re-run `simulate(..., trace=True)` on the window slice and print every buy/sell event with `initial` flags — exposes initial-inventory sales mixed into cycle counts.

Only after all three layers, concede or defend. This session's sz159615 case passed layers 1–3 and the honest answer was "9 cycles real, but 7 pure T + 2 initial-inventory sales, clustered on a rebound the window happened to open on".