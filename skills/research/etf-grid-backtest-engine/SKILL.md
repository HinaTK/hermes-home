---
name: etf-grid-backtest-engine
description: "Use when running or trusting the ETF grid backtest engine."
version: 1.1.0
category: research
---

# ETF Grid Backtest Engine — modeling rules

Governs `D:/Code/AH_analyse/tools/etf_research/` — `grid_model.py` (simulator A) and
`engine.py` (caller B). The engine is a 5-minute bar-by-bar simulator used to RANK
ETFs for grid suitability. It is not a forecast of the user's account.

## 1. Volume units — the classic silent killer

Sina 5-minute K-line `volume` is in **LOTS** (1 lot = 100 shares). Every share-denominated
quantity in the model (order qty, position size) is in **SHARES**.

Any comparison of bar volume to a share count must convert first:

```python
if core_qty + 4*q > vol[0] * 0.01 * 100:   # correct: lots -> shares
```

- Comparing raw `vol*.01` (lots) against share counts **wrongly rejects** any ETF whose
  first-bar volume is below roughly 2.3M shares, and **silently relaxes** the 1%
  participation cap by 100x for liquid ones.
- This broke low-turnover candidates (e.g. a 1.46M-lot first bar) exactly when they
  were being evaluated. Fixed 2026-10-14; all three comparison sites must be patched
  together — a partial fix leaves buy- or sell-side unchecked.
- After any volume-constraint change, re-run the affected holdings and confirm cycle
  counts moved for the right reason (constraint tightening, not a new data error).

## 2. Parameterize everything that the user can change

`simulate(frame, gap, t0, slip, trace, lot_budget)`:
- core position = `lot_budget * 2`
- initial trading lots = `lot_budget` each
- later rebuys = `lot_budget`
- `engine.run_research(..., lot_budget=..., gap=...)` passes them through.

Hardcoded 2% gap / 5000-per-lot defaults diverge from the user's live parameters
(1.5% gap, 6000/8000 per lot, gradual per-lot entry). Consequences:

- Absolute cycle counts and net spread from default parameters **cannot** be compared to
  the user's ledger. Report the divergence explicitly.
- A shorter gap means more grid lines in the same price range -> materially more round
  trips. A default-parameter run can understate a holding's real activity by an order of
  magnitude.
- Relative ranking INSIDE a pool that all used the same (even wrong) parameters remains
  valid, because the distortion is common to all candidates. Say which claim you are making.

## 3. Capital denominators must be actual

Any cycle-return metric divides by the capital actually employed
(e.g. `cycle_net / (4*c)`), never a hardcoded round number. A wrong denominator
understates efficiency by ~2x. Same rule for any "per-slot", "per-lot" or "per-capital"
ratio: derive it from the run, do not assume the nominal.

## 4. What the engine's outputs mean

- `cycles` / `cycle_net` = completed rebuy->sell grid cycles only. Initial-inventory
  sales are counted separately as `initial_sales` and are NOT grid profit.
- `cycle_net` is a spread measure, NOT account return. Inventory mark-to-market
  (`inventory_pnl`) and account P&L (`account_pnl`) are separate fields.
- Every ETF is simulated in its OWN normalized 100k account. Never add independent
  accounts together or present them as the user's joint-account forecast.
- `identity_error` (final - 100k - realized - open_pnl) must be ~0; treat a non-zero
  value as a hard failure, not a rounding note.
- The model is a next-open IOC approximation with slippage, not resting limit orders.
  T+1 is modelled as same-day buys being unsellable until the next session. No
  high/low path assumptions, no partial fills, no premium change modelling, no dividend
  reinvestment.

## 4b. Window semantics — the four windows are four INDEPENDENT simulations (2026-10-26)

- `engine.py` builds `{'full','early','late','recent20'}` as separate frame slices and calls
  `simulate()` once per slice. Each simulation anchors its grid at **its own first bar's open**
  (`initial_p = opens[0]`) with its own 100k account. They are parallel universes of
  "start the grid at that date" — NOT one simulation with sub-interval counts.
- Window counts are therefore **not additive and not nested**: `early + late != full`
  (159366: 1 + 6 = 7 vs full = 4) and `recent20 > full` ("倒挂") is a legitimate signal
  (all activity concentrated recently; a grid anchored at the lower recent price fits the
  recent range better), NOT a bug. When the user reasons "subset ≤ superset, so inversion
  is impossible" — the math is right, but the subset premise is wrong; say so explicitly.
- Usage split: `full_cycles` is the product-selection anchor (≥10 admission gate; stable
  across rolling windows). `recent20_cycles` is the temperature check (≥2 gate; catches
  both "dead now" and "only-alive-now"). Rolling windows swap ~5 sessions per week, so
  absolute counts are never comparable across research rounds — compare within one round.
- `entry_rank.window_matrix_label` (commit 4ccf3ba) renders the pairing per row:
  ✅双高 (full≥10 & r20≥2, candidate) / ⏳等信号 (high/low — often one-sided regime
  suppressing the grid; watchlist) / ⚠️脉冲 (low/high — probe-lot only, 159366-type) /
  ❌死水 (drop). Thresholds REUSE the admission gates exactly (MIN_FULL_CYCLES=10,
  MIN_RECENT20_CYCLES=2); never introduce a second standard. Boundary values are
  inclusive (r20=2 counts as high) — encode boundaries in tests, not in prose.

## 5. Known structural simplifications (state, do not silently "fix")

- Initial build fills 5 slots at the first bar; the user builds gradually per grid.
- The grid centre never re-bases; a price break beyond the range stops the grid.
- No partial fills — a volume-constraint miss cancels the whole order.
- 5-minute resolution can miss an intrabar touch that reversed within the bar.
- Changing any of the above invalidates historical rankings and requires a full re-run.

## 6. Workflow expectations

- Code changes to this engine follow the superpowers path: root-cause investigation
  (`systematic-debugging`) and RED->GREEN (`test-driven-development`) with a real failing
  test first. Post-hoc regression tests labelled as TDD are not TDD, and claiming the
  skill was used when it was not is a reporting failure.
- Tests must exercise the real production functions against temporary state, never
  invent production fills, and never touch live ledgers.
- After a fix, re-run the full suite and report the actual numbers.

## 7. Cross-border ETFs (QDII)

- Premium/discount is a real cost that the engine does NOT model. For cross-border
  candidates, fetch unit NAV and report premium alongside the simulated results; a
  positive premium erodes grid profit if it reverts.
- Trading hours differ (e.g. Japan 08:00-10:30 and 12:00-14:00 Beijing time) and the
  user's intraday monitor cannot cover them. A cross-border position is therefore a
  separate book, not a grid slot in the existing ledger.
- T+0 eligibility is a rule category, not a product name; generic QDII names are not
  T+0 by default.

## 8. Regime gate — the gate is part of the backtest (2026-10-27, commit 65e065e)

User rule: **backtest process must comply with the production gate** (「回测过程也要符合规则的哦」).
Never hand-roll a simplified gate for research; wire the production one in.

- `run_research(regime_gate=True)` computes `gate_check.blocked_buy_days(frame)` per ETF
  and passes `gate_days` into `simulate()`. Blocked days cancel **new-lot buys only**;
  initial build, sells, settlement, equity recording all untouched.
- **No lookahead**: day D's verdict is computed from daily bars through D-1 close
  (production: the 09:20 pre-market only knows yesterday's close). Blocked buys slide to
  the next unblocked day — global trade counts may NOT drop. Assert "zero new-lot buys ON
  blocked days", never "trades must fall".
- **Feed UNTRIMMED history**: `blocked_buy_days` needs ≥65 daily bars (entry_timing
  MIN_ROWS). The engine must pass full history, then keep only in-window dates. Feeding
  the 63-day window → 63<65 → fail-open → gate silently no-ops; signature: gated run
  byte-identical to ungated (all diffs 0.000). Zero-diff IS a failure signature, check it.
- **Never `continue` past the loop tail**: in `simulate`, the blocked-buy branch must skip
  only the purchase action. A `continue` also skips `equities.append` + invariant checks →
  equity curve loses blocked-day bars (1488 vs 1248), `final` reads a stale value,
  `identity_error` explodes (observed 200.8). The engine's identity check is what catches it.
- **ADX pause needs direction**: `ADX>=25 AND -DI>+DI AND close<ma60` (user's original
  10-26 rule). Without `-DI>+DI`, strong-momentum RALLIES get blocked; recovery legs stay
  blocked for weeks. This check was lost once in the merge and restored 2026-10-27.
- **Zero-impact per name is legitimate**: blocked days often coincide with bounces where
  no buy signal fires (589720: 22 blocked days, zero blocked buys → gated==ungated for it).
  Verify the gate works by counting affected names (198/283), not by requiring every ETF to differ.
- **Fixture pitfalls** (gate tests): daily bars need intraday range or ATR=0 → ZeroDivisionError
  in entry_timing; oscillation must exceed gap (±0.8% vs 2% gap → zero new-lot buys);
  recovery legs need ~15 bars for Wilder DMI to flip (8 is not enough — still blocked is
  CORRECT then); staircase crashes (-2%/day > gap) fire buy signals daily so the gate has
  something to block. Tests must add `tools/` to sys.path or `wilder_adx` fail-opens and
  single-run vs full-suite behavior diverges.
- Full-pool validation (283 paired, 63-day, gap 1.5%, lot 6000, offline same bars):
  account_pnl +183 mean, drawdown +0.45pp, end_cost −5128, min_cash +1293;
  affected-name distribution P10 −421 / P50 −73 / P90 +1862 — tail insurance, not return
  enhancement. Debugging transcript and re-run commands:
  [references/regime-gate-integration.md](references/regime-gate-integration.md)
