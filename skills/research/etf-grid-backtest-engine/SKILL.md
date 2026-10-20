---
name: etf-grid-backtest-engine
description: "Use when running or trusting the ETF grid backtest engine."
version: 1.0.0
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
