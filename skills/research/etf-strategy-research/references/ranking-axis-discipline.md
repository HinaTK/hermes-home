# Ranking axis discipline (user correction, 2026-10-16)

## What the user asked for vs what was delivered

The user asked: "本次排名前10是什么" and later "我他妈要的是往返次数排名".

The assistant delivered the composite `score` ranking (a weighted pct-rank blend of multiple metrics), labelled it "综合研究排名前10", and did not state the axis. The user's frustration was not that the score table was wrong — it was that the wrong axis was presented as the answer to a question about round-trip counts.

## The rule

**Default ranking axis for this user = `full_cycles` descending.** Tie-break by `full_cycle_net` descending, then by code.

Only use `score` when the user explicitly asks for a composite view, and then label it separately.

## Exact recomputation command

Given a `result.json` from `tools/etf_research`, the round-trip top-10 is:

```python
import json
from pathlib import Path
r = json.loads(Path('.../result.json').read_text(encoding='utf-8'))
eligible = [x for x in r['ranking']
             if x.get('has_all_four_windows') and x.get('full_cycles') is not None]
eligible.sort(key=lambda x: (-x['full_cycles'], -x['full_cycle_net'], x['code']))
for x in eligible[:10]:
    print(x['code'], x['name'], x['full_cycles'], x['full_cycle_net'])
```

Do not trust `result['rotation_top10']` — in the 2026-10-16 run it was empty while `ranking` had 310 eligible rows.

## Context that must accompany every ranking table

- Window start / end dates and session count
- Universe size, attempted assets, eligible rows, failed windows
- Whether current holdings are included or excluded
- Whether Hong Kong / cross-border names are in or out
- That net差价 excludes open-inventory P&L and is modelled, not realised

## Concrete 2026-10-16 numbers (for reference, not to be reused as current)

Window 2026-07-14 → 2026-10-16, 63 sessions, 321-asset historical eligibility pool, 310 rankable, 44 failed windows.

Round-trip top-10 (full_cycles desc): sh589720 37 / sh520690 31 / sh589120 31 / sz159217 30 / sz159316 30 / sz159570 27 / sz159297 27 / sh520500 26 / sz159286 24 / sh562800 24.

Holdings in that ranking: 589720 #1, 159992 #21 (20 cycles), 159363 #31 (17 cycles).

Composite-score top-10 (different axis, do not conflate): sh512980 0.920 (22 cycles) / sh516860 0.892 (14) / sz159851 0.877 (14) / sh516010 0.846 (23) / sh512200 0.835 (16) / sh516650 0.835 (12) / sz159652 0.832 (12) / sh513040 0.825 (14) / sz159531 0.822 (18) / sz159876 0.805 (12).

Note that composite #1 (22 cycles) is not round-trip #1 (37 cycles). This is the exact trap the rule exists to prevent.

