---
name: etf-grid-maintenance
version: 1.0.0
category: trading
description: Use when maintaining ETF grid trading system.

---
# ETF Grid Maintenance Skill

This skill encapsulates the routine tasks for operating a 2% grid trading system on ETFs via Hermes Agent.

## Triggers
- User asks to clean up unconfirmed buy/sell orders after a session.
- User requests closing price collection and storage for the day.
- User wants to verify that the grid ledger is consistent with broker fills.
- User needs to generate next-day operation suggestions based on closing data.

## Workflow
1. **Collect Closing Prices**
   - Use the existing 15:20 scheduled task (`grid_eod_decision.py`) to download verified day‑line data from Tencent and store it in `cache/grid-account/eod/YYYY-MM-DD.json`.
   - This step is already automated by the cron job `b3097b45fafa`.
2. **Clean Unconfirmed Orders**
   - After the closing data is stored, run `cleanup_after_close(book)` (added to `grid_eod_decision.py`).
   - This function:
     * Empties `migration.json → historical_unconfirmed_buy_orders` (treats unconfirmed buys as failed and releases internal reservation).
     * Removes any zero‑quantity entries from each position’s `rebuy` array.
   - It does **not** modify cash, qty, or cost_cash in the ledger, nor does it send any broker orders.
3. **Verify Ledger Integrity**
   - Check that every entry in `ledger.json → history` has `result: "成功"` (only confirmed fills are recorded).
   - Ensure that `migration.json` reflects the current migration stage (source/target, caps, etc.).
4. **Generate Next‑Day Suggestions**
   - The same `grid_eod_decision.py` script produces a preview note for the next trading session (9:31 advice) and stores it in the day‑specific EOD file.
   - The note is pushed to Feishu via the `e01b833b150d` job.

## Pitfalls
- **Do not run cleanup before the session closes** – the function assumes the market is closed and will not interfere with live orders.
- **Never edit `ledger.json` directly**; all changes must go through the validated functions in `grid_account.py` and `grid_eod_decision.py`.
- **Zero‑quantity rebuy entries** are harmless but accumulate; the cleanup function removes them to keep the book lean.
- **Historical unconfirmed buy orders** are only an internal reservation; the actual broker fill remains authoritative if later reported.
- **Migration guard can crash the intraday cron job** – `grid_migration.py:load_policy()` raises `ValueError` when `migration.json` has `target_buy_enabled: true` without manual broker verification. This propagates through `grid_weixin_intraday.py:trend_alert()` → `guard_ticket()` → `load_policy()` and kills the `ef9a27327990` (盘中检查) cron job. See `references/migration-guard.md` for the full error surface and recovery steps.
- **Cost basis model (2026-10-09 user-corrected)** – `pos["cost_cash"]` must equal **net invested = total buy costs (含费) − total sell proceeds (含费)**, NOT the sum of remaining lot buy costs. A sell does **not** reduce the cost basis of remaining shares; the user tracks total money put in minus total money taken out. The old `apply()` logic subtracted `take × source["price"]` from `cost_cash`, which understated the basis and produced a phantom "浮盈". The correct sell path in `apply()` is: `pos["cost_cash"] = round(pos["cost_cash"] - proceeds, 2)` where `proceeds = notional - commission`. Rebuild cost_cash from `history` by summing per-code buy costs and subtracting per-code sell proceeds; never derive it from lot-level arithmetic after a pooled T+1 sell.
- **Pooled T+1 sell does NOT consume the target lot** – when a sell hits a grid price (e.g. C格) whose lot was bought same-day (T+0), the shares are drawn from the pooled T+1 inventory (oldest settled lots first, FIFO), **not** from the target lot. The target lot's `qty` stays untouched. The old code zeroed the target lot's qty, which desynced `pos["qty"]` from the sum of lot qtys. Always call `sync_qty(pos)` after a sell so `pos["qty"] == sum(lot["qty"])`.
- **When reconciling with the user, compute cost basis from history, not from lot state** – the user will independently sum `buy costs − sell proceeds` and compare against `cost_cash`. If the numbers differ, the discrepancy is almost always in the sell-side cost reduction path, not in the buy records. Walk through each trade one at a time; the user will correct you down to the yuan.

## Reference Files
- `references/grid_eod_decision_overview.md` – brief explanation of the EOD decision script.
- `templates/cleanup_after_close_stub.py` – starter implementation if the function ever needs to be recreated.

## Example Usage
User: "1.363的挂单撤回了 2.992残留可以清理 3.收盘数据可以在15.20那个定时任务里面统计，同时也清理所有未成交的买单和卖单记录"
Agent: (already performed) – see the session log for the patch to `grid_eod_decision.py` and the verification that the cleanup ran successfully.
