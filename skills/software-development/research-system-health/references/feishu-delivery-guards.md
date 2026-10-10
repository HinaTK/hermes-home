# Feishu / WeChat delivery guards (AH_analyse)

Official path: `stock_recommend.run` → `--push` → `AH_FEISHU_WEBHOOK` (optional `Downloads\\feishu_key.txt`). Scheduled via `python -m scheduler.daily_job --mode pre_market|open_confirm|post_market --push`. `run_daily_job.py` / `--mode legacy` does not push.

## Why wrapper-only guards fail

`run_pipeline` skipped Feishu on quality failure, but `_deliver_report` still called `push_to_feishu`. Post-market error reviews and WeChat used that path. Tests once asserted quality-failed reports **did** hit Feishu once. `POST /api/v1/recommendations/notifications/test` calls `push_to_feishu` directly.

Put mock + quality blocks in:
- `_deliver_report` (before `should_deliver` / `force`)
- `push_to_feishu` (before `requests.post`)
- `push_to_wechat` (before `requests.post`)

Mock preview encoding tests must use a live `coverage` fixture if they need to reach the content-audit gate; otherwise mock block wins first.

## Session collision

Idempotency key is `{trade_date}:{session}`. `evening_pre_market` with `force_push=True` re-sends the morning `pre_market` card. Prefer `force_push=False` and a separate snapshot job that does not push.

## Card vs UI

Pre-market: `CONDITIONAL_BUY` + 条件买入 zone/stop/target + 仓位 + 开盘确认前不得成交.
Open-confirm (`session=open_confirm`, `latest_open_confirm.json`): `BUY` → 可下单; `CANCEL` → reason, no replacement. Does not overwrite `latest.json`.
Do not print scaled confidence as a ticket. After installing tasks, `AHAnalyse-OpenConfirm` is 10:00.

## Silent morning: empty history on previous-close replay

Symptom: Task ran (`AHAnalyse-PreMarket` last run ~08:06, exit 1), `latest.json` exists, Feishu empty. Typical fields:
- `coverage.source=previous_close`, scanned thousands of rows
- `history_count=0`, `history_target_count=30`
- `quality_gate.blocking_reasons`: 候选历史行情完整率低于80%
- `delivery.reason=quality_gate_failed`
- no `trade_date:pre_market` in `delivery_ledger.json`

Cause: replay skips live K-line enrich, snapshot rows lack `history_days`, gate still requires 80% on the ranked 30.

Fix pattern (landed `048884c`):
- 17:30 snapshot: `_enrich_with_daily_features(..., limit=min(n, 600))` then persist
- open: enrich at most 30 ranked candidates even on replay
- `quality_gate`: previous_close / disk_cache history gap → **warning**, not blocker
- collect with no rows: return before `build_candidates` / rule scan
- `push_failure_alert` for failed live runs; mock still blocked
