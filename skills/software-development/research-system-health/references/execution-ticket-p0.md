# Execution ticket P0 (AH_analyse official path)

Landed `464680e` on `feat/evidence-based-stock-recommendation` after the user rejected WATCH-as-product: they want **buyable tickets**, not an observation diary.

Do not write a personal BUY from a pre-market JSON that is still `WATCH` / yesterday's close.

## Buyable standard (must all hold)

1. Action is `BUY` at send time, **or** `CONDITIONAL_BUY` that says 开盘确认前不得成交.
2. Trigger verified at send time, or a later `open_confirm` session verifies it.
3. Reward/risk of the printed plan ≥ 1.5, else no formal ticket (`reward_risk:` rejection).
4. Position is on the ticket: defense 5%–8% name / ≤30% account; else name cap 10%.
5. Open confirm: in-zone + amount ≥ 20d mean → `BUY`; gap-up / low volume / sector ≤ −0.5% → `CANCEL`, **no replacement names**.

Quality-gate pass ≠ buyable. Composite / `0.45+0.4×composite` confidence ≠ win rate.

## Code map

| Piece | Where |
|---|---|
| Formal action, RR gate, size | `rule_selector.select_by_rules` |
| Confirm / cancel | `open_confirm.confirm_open_picks` |
| Job, quotes, persist | `run.run_open_confirm` — writes `latest_open_confirm.json`, **does not** overwrite `latest.json` |
| Scheduler | `--mode open_confirm`; CLI `--open-confirm` |
| Task | `AHAnalyse-OpenConfirm` 10:00 via `tools/install_stock_recommend_tasks.ps1` (re-run installer) |
| API | `GET /api/v1/recommendations/open-confirm` |
| Tests | `tests/test_execution_ticket_p0.py` |

Delivery session key `{trade_date}:open_confirm` is independent of `pre_market`.

## Not in P0

- Event placeholder 0.5 / “无法判断吸筹” as supporting capital (P1)
- WATCH-aware / trigger-aware backtest vs HS300 (P2)

A already-written `latest.json` stays old-WATCH until the next pre-market job.

## Open-confirm ops (2026-09-23)

Code landing `AHAnalyse-OpenConfirm` is **not** enough. The Windows task must be re-installed after the installer change; until then 10:00 will not fire. Diagnose a missing 10:00 card from `schtasks /Query /TN AHAnalyse-OpenConfirm` first.

`_lookup_open_quotes` must read `SnapshotResult.rows` (not `snap.fundamental`) and prefer focused Tencent/Sina quotes for the ticket codes. Quote/API failure is a red `push_failure_alert`, never a formal `CANCEL` with `quote_missing`. Gap-up out of zone is `gap_up` only — do not stack a fake `volume` cancel when 20d amount is absent.
