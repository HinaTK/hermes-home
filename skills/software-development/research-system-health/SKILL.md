---
name: research-system-health
description: "Use when auditing or repairing stock-research systems."
---

# Research System Health

Class of work: make a research/recommendation codebase honest and testable — not add more factors until data, time windows, and quality checks can be trusted.

Canonical instance in this workspace: `AH_analyse` / `ah_recommendation_system/` (see repo `AGENTS.md`). Apply the same pattern to similar pipelines.

## Default sequence

1. **Health check before new models.** Map entrypoints, stored vs live data, mock vs network, quality gates, and what the UI actually labels. Write findings as verified vs risk with file:line.
2. **Do not treat scores as edge.** Quality-gate pass, ML confidence, and backtest PnL are not win rates until execution timing, costs, and independent baselines check out.
3. **Fix in this order:** (a) backtest/settlement honesty, (b) coverage denominators, (c) explicit demo/stale labels, (d) outage fallbacks that keep old timestamps, (e) only then ranking models.
4. **TDD on the failing behavior**, then the smallest production change. Watch the new test fail for the real bug, not an import error.
5. **Keep live market I/O out of the default test run.** Allow loopback; block external sockets. Mock mode must skip live ETF/sector collectors, not just price_fetcher.

## What “trustworthy” means here

- Every card shows **source, quote basis, generated_at, and validity**. Previous-close scans must not be presented as intraday strength.
- Demo valuation (fixed PE/PB/yield) and scaled-magnitude “confidence” must be labeled **not investment-usable**.
- History completeness: denominator = intended candidate set; numerator = same set with enough history. Never count only successes as both.
- Ranker promotion needs an **independent composite baseline**, dated top-N cohorts, and real drawdown (or explicit unavailable → no promote). Same-model vs itself is not a baseline.
- Pair/mean-reversion backtests: **settle the old position on today’s move, then trade on the close signal.** Missing z-score must still settle held PnL. Entry costs belong in trade pnl.
- Live upstream exceptions: fall back to stored reports with `fresh_data_available=false` and a non-realtime warning; do not mint a new timestamp. No stored report → keep the failure.
- Missing returns in UI: show “待验证”, never `Number(null) === 0` as `0.00%`.

## Quality-gate pitfall

Tighten live-run stats without treating **research cards that never ran a history cohort** as failed coverage. If both `history_target_count` and `history_count` are absent, there is nothing to measure. If a live `source` is set, require explicit `fresh_data_available is True`. Existing empty-report / hotspot-push fixtures will go red if you fail missing freshness on cards with no source.

When a pipeline test goes empty after a denominator fix, **give the fixture real history/pe rows** rather than loosening the gate.

**Previous-close replay vs empty history (do not silent-skip Feishu):** A morning job that prefers last night's snapshot and skips `_enrich_with_daily_features` will report `history_count=0` on ~30 candidates even when the snapshot has thousands of rows. Treating that as `quality_gate_failed` looks like “no pre-market push”. Prefer: write `history_days` on the 17:30 snapshot (capped, not whole-market K-line), enrich **at most the ranked 30** at open, and on `source=previous_close` / `quote_basis=previous_close` demote history completeness to a **warning**, not a blocker. Collect failure must stop before the 10-minute rule scan. Failed runs send `push_failure_alert` (red “任务异常”, no names / buy ticket), not a formal CONDITIONAL_BUY/WATCH card and not silence.

## Isolated unittest (Windows / this stack)

See `references/isolated-unittest.md` for the socket-patch snippet and mock-report gate.

- `PYTHONPATH` = repo root **and** `backend/` (some tests import `stock_recommend.*` bare).
- `AH_HOURLY_REFRESH=0`, `PYTHONDONTWRITEBYTECODE=1`.
- Patch `socket.socket.connect` to allow `127.0.0.1` / `::1` / `localhost` only. A total connect block breaks FastAPI `TestClient` (Windows `socketpair`).
- Default `python -m unittest discover` can hit real AKShare/Eastmoney and hang on retries — do not call that “all tests passed” if you had to kill it.
- Keep regression tests next to the bug: `test_*_regression.py` for outage fallback, coverage denominators, backtest timing, ranker baseline, mock-offline ETF skip, legacy demo labels.

## Output contract for the user

Lead with what is now safe vs still not proven. Do not claim strategy edge. Prefer a short table of fixes and a path to the health-check note.

**Product goal (corrected 2026-09-22):** this user wants the official path as **explicit buy tickets**, not an observation diary. Do not lecture 「个股只是观察候选」 or 「怎么守住 WATCH」 after they said they use the push to buy. Answer **whether the push meets a buyable standard**, what is missing, and how to close it. Do **not** invent a personal BUY from a WATCH / yesterday JSON (no 歌尔今天买 6%–10%).

When asked how an **investment researcher** should view the official path (not a code audit), judge **process honesty vs proven edge**, then **buyable-standard gap**. Rubric: `references/recommendation-path-research-judgment.md`. Execution-ticket P0: `references/execution-ticket-p0.md`.

- Usable as environment: previous-close quote basis, empty book, quality-gate refusal to speak.
- Pre-market formal action is `CONDITIONAL_BUY` (not WATCH, not BUY). Open-confirm session may promote to `BUY` or `CANCEL`.
- Not edge: composite weights, `0.45 + composite × 0.4` confidence, PE/momentum screens as a company thesis, T+N fills that ignore the open-confirm trigger.
- Do not promote adding factors. Dual engines (`select_by_rules` vs `recommendation_policy` contract layer) are a research-口径 risk, not a product next step unless the user asked.

When you say a leftover pipeline is 「不当正式推荐」, also say it still runs if it still runs (legacy report, force-refresh, extra tabs). Demo labels are not deletion.

If asked whether a specific entry pushes notifications, name the entry that **does** in the same answer. For this app, Feishu is `stock_recommend --push` / scheduled `pre_market|open_confirm|post_market --push`, not `run_daily_job.py`. Details: `agreed-plan-execution` → `references/ah-analyse-official-path.md`.

## Notification delivery (Feishu / WeChat)

A pipeline `if quality_failed: skip` is not enough. Guard **at the send function** (`push_to_feishu`, `push_to_wechat`) and at `_deliver_report`, because post-market error reviews, `--force-push`, and `POST /notifications/test` bypass the pipeline wrapper.

Block **formal** delivery before HTTP:
- mock (`coverage.mode=mock_sample` / `source=mock`) even with `force`
- `quality_gate.passed is False` or `run.status == failed` — do **not** send the decision / CONDITIONAL_BUY / BUY card
- post-market when `latest.json` is not today’s pre-market report: save the error review, do not push a review card
- `open_confirm` uses session `open_confirm` (idempotency key `{trade_date}:open_confirm`); it must not overwrite `latest.json`
- `evening_pre_market` must not `force_push=True` against the same `trade_date:pre_market` session as the morning job

Failed live runs still notify via `push_failure_alert` (separate red card, no names/buy zones). Mock stays blocked on that path too. Diagnose a missing morning push from `latest.json` `delivery.reason`, `quality_gate.blocking_reasons`, `coverage.history_count` / `history_target_count`, and Task Scheduler last-run exit code — not from webhook config first.

Card copy must match the **execution** surface:
- Pre-market `CONDITIONAL_BUY`: zone / stop / target / position + 「开盘确认前不得成交」. Never print a market BUY.
- Open-confirm `BUY`: 「可下单」 + zone / stop / position. `CANCEL`: reason, no replacement names.
- Do not render scaled `confidence` as a win rate. UI and webhook can drift independently — audit both.

Regression file in this repo: `tests/test_feishu_delivery_guard.py`. Session notes: `references/feishu-delivery-guards.md`.
