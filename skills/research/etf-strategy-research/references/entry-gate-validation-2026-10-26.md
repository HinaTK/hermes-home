# Entry-gate rule validation — unified gate_check case (2026-10-26)

Origin: user found two "don't buy in downtrends" checks (entry_timing 榜单禁入 vs RegimeGate EOD 暂停买) overlapped and conflicted — 589720 was five-lines-broken yet passed by ADX 17.3. After merging (commit 8101603), user challenged the merged rule twice (589720 earning well while "banned"; boundary at exactly −0.5%), then explicitly authorized data-first treatment: the original 五线全破 rule was their intuition without basis and must be validated, not blindly kept or merged.

## Final system (tools/etf_research/gate_check.py)

Four levels, strictest wins, sells never blocked, missing data fail-open:

1. 暂停买入（五线全破）: close < ma5/10/20/30/60 all five. Release = close back above MA5 (automatic, next check).
2. 暂停买（强动能跌势）: ADX≥25 AND close < ma60.
3. 试错仓: 1–4 lines broken; carries 20-day-low exit price.
4. 正常: above MAs.

Engineering invariants: single implementation (gate_check calls entry_timing.judge_entry; below_count exposed as a field, never parsed from reason text) and single data source (fetch_daily_regime fetches one kline batch for both ADX and MAs). RegimeGate in confirmed_runtime.py keeps its interface; plan() untouched. Deploy path: scripts/grid_weixin_execute.py sys.path-points at the repo — commit = deploy for the 09:20 premarket job.

## Validation evidence (cache 20261026-200137-313253, 201–321 covered ETFs)

Pooled per-ETF×day samples, n=7,743:

| below_count | n | fwd-20d cycles | fwd-20d max DD | terminal ret |
|---|---|---|---|---|
| 0 | 1,377 | 3.47 | −5.15% | −2.73% |
| 1–2 | 2,045 | 3.49 | −6.3% | −4.4% |
| 3 | 1,091 | 3.28 | −6.25% | −4.13% |
| 4 | 1,102 | 2.70 | −6.89% | −5.09% |
| 5 | 2,128 | 2.47 | −7.96% | −6.28% |

Monotone decay, steepest jump at 4→5 → the user's rule survives; "fifth line broken" is a phase change, not linear worsening. Full-break P10 further drawdown: −14.3%.

## Rejected refinement variables (do not re-propose without new evidence)

- **ADX stratification within full-break** — no gradient: cycles by ADX band <15: 2.23; 15–20: 2.70; 20–25: 2.17; 25–30: 2.67; 30–40: 2.52. Any cut at 20/25/30 separates by ≤0.3 cycles, direction inconsistent.
- **Deviation-from-MA5 depth** — non-monotonic (worst bucket −1.25~−1.5% at 1.80 cycles; −3%+ rebounds to 3.69). Day-to-day deviation noise: P25 −0.98pp / P75 +1.11pp, 69% of days move >0.6pp → any hysteresis band narrower than ~1.5pp is crossed daily; single-point thresholds flip on 2 ticks for a 0.8-CNY ETF (0.001 tick = 0.125% deviation).
- **Bucketing artifact warning**: the first coarse run (buckets −2/−1/−0.5/0) produced a spurious 「贴线组 3.71 最高」 conclusion; fine 0.25–0.5% cuts showed hugging-MA output is actually 2.38–2.45, indistinguishable from deep pressure. Conclusion flipped with bucket boundaries → variable is noise-carrier, rejected.

## Event-level dual simulation (n=573 first-entry-into-full-break events)

From each event, 20 sessions forward, rule-on (no new lots while full-break) vs rule-off (keep buying), 1.5% gap, 8,000/lot:

- Gate wins 221 / no-gate wins 305 / tie 47 — **no-gate wins the majority of events**
- Mean delta +121 favor gate; median −75 against → insurance structure: small frequent cost, rare large payoff (P90 +1,135)
- Rule-off averages +12,033 extra capital occupation per event
- Verdict: the rule is **tail insurance + capital preservation, not a return enhancer**. 39% of full-break events were profitable in the next 20 sessions → 「禁入/banned」 overstated; renamed 「暂停买入/pause」 with release condition in the text, zero behavior change (commit c0b051e, 145/145 tests).

## Pulse vs persistent full-break (why per-ETF experience differs)

- **589720 pulse-type**: 23/123 days full-broken, 9 on/off switches in 30 days, longest run 8 days (10-08~10-19 — which was actually its productive T-window), current streak 1 day. Pausing costs little; user's realized 14 rounds × T-profit continued through full-break days.
- **159363 persistent**: full-break + ADX 36 double confirmation — the pattern the rule exists for.

## Reproduction pointers

- Tests: test_gate_check.py (6), test_regime_gate.py UnifiedGateTests (4), full suite 145/145.
- TDD trail for the rename: test_no_entry_label_says_pause_buy_not_ban (RED on 「不能建仓」, GREEN on LABELS).
- Validation scripts were session-ephemeral pool scans over bars/*-m5.csv (prepare/_levels + local Wilder ADX). Forward cycles measured on close-price path — coarser than the 5-min engine; gradient direction reliable, absolute counts approximate.
- Boundary values in the final system (MA5 release line, ADX 25) are the user's original parameters or engineering choices; the data fixed only the semantics and rejected the extra cuts.
