# Regime-gate integration into the backtest engine (2026-10-27)

Commit 65e065e. Trigger: user asked to re-run the 573-event gate validation "according
to the rule" — the hand-rolled validation had lookahead (same-day close judged same-day
buys) and omitted the ADX pause tier. The production gate had never been wired into the
engine at all.

## What shipped

- `gate_check.blocked_buy_days(m5_frame)` — per-trading-day verdict; day D judged on daily
  bars through D-1 close; ≥65 bars or fail-open (production semantics); reuses `wilder_adx`
  from `market_phase_check` (single ADX source) and `entry_timing.judge_entry` via `gate()`.
- `grid_model.simulate(..., gate_days=None)` — blocked day cancels the new-lot buy only.
- `engine.run_research(..., regime_gate=False)` — computes gate per ETF from UNTRIMMED
  `data[c]`, then filters to in-window dates; passes same dict to all four windows.
- `gate_check` ADX pause restored `mdi > pdi` direction check.

## Bug discovery order (all real, all fixed via RED→GREEN)

1. **Gate absent from engine** — every prior research run was ungated. Hand-rolled event
   studies had lookahead + missing tiers.
2. **`continue` skipped the loop tail** — blocked-day equity bars never appended
   (curve 1488→1248 bars); `final=equities[-1]` read a stale value; `identity_error`=200.8
   (≈ one deferred lot's worth of drift). The engine's identity invariant caught it.
3. **Windowed data fail-open** — first wired version fed the 63-day window; 63<65 → all
   False → gated run identical to ungated, every diff 0.000. Caught by "results identical"
   being itself a failure signature; regression test proves 63-bar input cannot judge.
4. **Missing `-DI>+DI`** — bounce legs blocked (strong momentum UP treated as crash);
   exposed only when `market_phase_check` was importable (full-suite vs single-run
   divergence → sys.path lesson below).

## Fixture lessons

- All-same-price 5m bars → `high==low` → ATR=0 → ZeroDivisionError in `entry_timing`
  extension calc. Give ±0.4% intraday range; close on last bar.
- Oscillation amplitude must exceed gap: ±0.8% vs 2% gap → zero new-lot buys, nothing to
  block. Use ±3% (or gap-relative staircases).
- Recovery must be long enough for Wilder DMI to flip: 8 bounce bars → -DI still dominant →
  still blocked (CORRECT rule behavior; the fixture expectation was wrong). ≥15 bars.
- "Blocked buys slide to next day": total trades may be unchanged. Assert per-day zero
  buys on blocked days; do NOT assert `trades` monotonicity or `end_cost <=` (deferred
  buys at recovery prices cost the same, float tail ±1e-12 either sign).
- Gate tests must insert `tools/` into sys.path, else `wilder_adx` ImportError → ADX
  branch fail-opens and behavior differs between single-run and full-suite runs.

## Full-pool validation (63-day window, gap=0.015, lot_budget=6000, offline, same bars)

198/283 full-window runs materially affected:

| metric | ungated | gated | diff |
|---|---|---|---|
| cycles | 9.17 | 7.24 | −1.93 |
| cycle_net | 964 | 760 | −203 |
| account_pnl | −4153 | −3969 | +183 |
| max_drawdown_pct | −7.95 | −7.50 | +0.45pp |
| end_cost | 43073 | 37945 | −5128 |
| min_cash | 54076 | 55369 | +1293 |

Affected-name pnl diff: P10 −421 / P50 −73 / P90 +1862 — tail insurance.
Holdings: 589720 zero impact (22 blocked days all landed on bounces, no buy signals
blocked); 159363 18→15 cycles, net 2042→1801 (the insurance-cost case); 159992 unchanged.

## Re-run recipe

```python
from tools.etf_research.research import run_research
BARS = 'D:/Hermes Agent CN Desktop/data/hermes-home/cache/grid-research/20261026-200137-313253/bars'
for tag, gate in (('gated', True), ('ungated', False)):
    run_research(
        input_path='D:/Hermes Agent CN Desktop/data/hermes-home/cache/grid-broad-20260923',
        bars_dir=BARS,
        output_path=f'.../grid-research/{tag}-<date>',
        offline=True, sessions=63, lot_budget=6000, gap=0.015, regime_gate=gate)
# then join runs.csv on (code, window), diff every metric, count affected names
```

Offline + same bars_dir = byte-comparable pair. `successful_runs` 1066 / `failed_runs` 218
(166 of the failures are the legitimate 1%-first-bar-volume model exclusions).
