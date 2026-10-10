# AH_analyse: official vs leftover flows

Official product path (conditional tickets → open confirm; not a proven-edge system):

- `ah_recommendation_system/backend/stock_recommend/`
- UI default: 每日推荐 / 盘前决策卡（条件买单）
- APIs: `/api/v1/recommendations/pre-market`, `open-confirm`, `post-market`
- Scheduler modes: `pre_market`, `open_confirm`, `post_market` (plus previous-close snapshot and weekly reweight as helpers)
- Formal pre-market action: `CONDITIONAL_BUY`. Only `open_confirm` may send `BUY`.

Still in the repo, **not** official recommendations:

- 配对交易 / 多因子 / ML under 更多策略 (demo; fixed PE/PB; ML confidence is not a win rate)
- Legacy daily report: `run_daily_job.py` + `data/daily_reports/` (scheduler default `legacy`; UI 强制更新 still hits this)
- ETF&板块: still a primary tab, independent module, not the stock-pick mainline

When the user asks which flow survived coexistence: answer the table above. Do not claim the others were deleted.

## What 可信度整理 actually did

Anti-misuse, not a merge: demo flags on multi-factor/ML, UI default to the decision card, leftover strategies under 更多策略, quality/coverage/backtest honesty on the new path. `run_daily_job.py`, multi-factor, ML, and force-refresh of the old report still exist.

## Feishu / WeChat delivery

Pushes **new** `stock_recommend` cards only.

| Pushes Feishu | Does not |
|---|---|
| `python -m scheduler.daily_job --mode pre_market --push` (and `open_confirm --push`, `post_market --push`) | `run_daily_job.py` / `--mode legacy` (只写 `data/daily_reports/`) |
| `python -m ah_recommendation_system.backend.stock_recommend.run --push` / `--open-confirm --push` | previous-close snapshot, weekly reweight |
| Windows tasks from `tools/install_stock_recommend_tasks.ps1` (`AHAnalyse-PreMarket` / `OpenConfirm` 10:00 / `PostMarket`) | |
| `POST /api/v1/recommendations/notifications/test` | |

Webhook: `AH_FEISHU_WEBHOOK` or local `Downloads\feishu_key.txt`. Optional `AH_FEISHU_SECRET`. WeChat: `AH_WECHAT_WEBHOOK` (optional, same report).

Do not persist this repo's session plan into cross-session memory unless the user asks. In-session: follow the last agreed sequence; field-audit extras (涨跌幅 / PE / 价格日) are notes, not the next product step.
