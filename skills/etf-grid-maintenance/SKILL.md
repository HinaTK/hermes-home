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

## Authoritative reconciliation and safe rebuilds
- When the user says “只以我刚给出的数据为准，其他抛弃”, replace evidence for the named ETF only. Do not import old suggestions, inferred fills, or dates; do not reset other ETFs or the entire account.
- Display reconciliation **separately by ETF, in supplied execution order**, with stable row IDs, direction, quantity, price, and source. Include initial A-grid purchases. Suggestions are not transactions; ticket `pending` does not prove that a user never confirmed a fill elsewhere.
- Inspect explicit `partial_fills` and `filled_action` independently of whole-ticket status. “已部分成交-归档” does NOT make all its `actions` executed. Assistant-created success flags are not independent broker/user confirmation.
- Preserve unique execution IDs and explicit buy→sell references for each grid cycle. Repeated G/C rebuy cycles must not be deduplicated merely because their date, quantity and price match. Keep economic grid matching separate from physical T+1 FIFO inventory consumption.
- Unknown execution dates stay null. Sequence numbers are not dates; never advance one trading day per trade. With missing dates, report sellable quantity as unknown and block automatic executable suggestions based on that subledger.
- Before replay, inspect helper side effects: `seed()`, `load()`/migration and `apply()` may write live state. Tests and dry-runs must use isolated temporary paths or pure builders, never production seed/apply. Back up the original bytes BEFORE any mutation; restoring a backup created after damage is not recovery.
- Rebuild in memory, validate and compare, then atomically persist and read back the exact target. Do not replay every pending ticket, disable safeguards to force replay, or append historical fills to an existing balance (double-counting).
- TDD requires a real RED→GREEN cycle against production behavior. Do not implement arithmetic inside a test and call that a tested production path. Test imports must not seed live ledgers. Cover repeated cycles, idempotent replacement, fee allocation, date uncertainty and scope isolation.
- Report net invested (buy including fees minus sell net proceeds), its per-share value, and completed grid net profits separately. Remaining economic-grid purchase cost is not physical FIFO inventory cost. A standalone subledger is NOT proof that live ledger/automatic suggestions are integrated; account cash remains unverified if other ETFs are unreconciled.
- See `references/authoritative-trade-rebuild.md` for a verified nine-trade numerical fixture and acceptance boundaries.

## Stateful grid labels and cycle identity
- Grid labels are **derived state, not manually supplied trade inputs**. Under the user's current A–Z stack rule, maintain each ETF's current maximum sequence separately: no open grid = null; buy assigns successor(max), then advances max; sell assigns current max, closes that economic grid cycle, then decrements max. Replaying a complete authoritative history starts from null; incremental fills read the stored per-ETF state.
- Persist the generated label in each trade record (`lot`/grid field) along with unique execution ID; persist current maximum in the ETF summary. Never derive current maximum from the highest letter ever seen in historical/zero-quantity lots: a completed E sale must move E→D.
- Rebuying C after selling C is a new C cycle, not a new D or a manually named surrogate. Store explicit buy execution ID→sell execution ID links; grid letter alone cannot identify a cycle. Reject unmatched sells, Z overflow and unsupported partial-grid closes rather than guessing a pairing or decrementing prematurely.
- These labels track **economic grid cycles**, not physical inventory lots. Selling the current grid still requires enough pooled settled T+1 inventory; do not replace pooled settlement rules with target-grid settlement rules.
- When asked whether all data came from a script, distinguish user-supplied inputs, manually configured parameters, automatically derived fields and actually persisted output. “Present in script output” does not mean “automatically derived.” Do not claim label automation if labels were hardcoded in the input.
- See `references/stateful-grid-labels.md` for the regression fixture and integration acceptance checklist.

## Persisted inventory and midnight scheduling
- `sellable_qty` is a user-required **persisted mutable state variable**, alongside `qty` and `max_grid`; it is not a report-time interpretation. Read it from the stored ETF state when validating a sell. Script changes must save it atomically and survive process restart.
- The requested daily 00:01 transition recomputes holdings from authoritative transaction records and writes `sellable_qty = qty`. Intraday confirmed buys increase `qty` only; sells first validate the saved sellable pool, then reduce both values. Do not reset sellable inventory every time a script starts.
- Unknown original execution dates must remain unknown, but do not use that uncertainty to refuse the explicitly requested midnight state transition. Keep the date evidence separate from the user's inventory-state rule. Broker availability and frozen orders remain a separate execution check.
- Make midnight rollover idempotent by storing its update date: a repeated invocation on the same date must not restore inventory already sold intraday. Validate duplicate execution IDs and negative inventory before writing. Test disk readback, same-day repeat after a sale, buy/sell transitions, insufficient-inventory rejection without mutation, and unchanged grid pointer.
- Use the Superpowers-derived TDD skill for implementation: observe missing-behavior RED, implement, then GREEN. Test production functions using temporary state files, never invented production fills. Preserve other ETFs and unrelated fields.
- A function is not a deployed schedule. List existing cron jobs, create/update one pure-script daily `1 0 * * *` task, then read back enabled state, exact script, timezone/next run, and target file. Distinguish temporary-file execution tests, actual scheduled-script execution, and first overnight scheduler execution; do not claim one proves the others.
- A working standalone subledger does not satisfy integration into the existing fill-confirmation/09:31 suggestion path. Report the exact state files and ETF coverage; never imply all ETFs are covered when only the reconciled one is registered. Incremental confirmed fills must use the same state update path that midnight maintenance targets.
- See `references/persisted-inventory-rollover.md` for session evidence and deployment acceptance boundaries.

## Script-only reports and multi-ETF expansion
- When the user asks that every reported value come from scripts, read the exact persisted target first and independently recompute from its stored trades without mutating it. Report the actual saved `sellable_qty`, including null; temporary-file test output is never evidence of live initialization. Do not run rollover merely to make a report look complete.
- All displayed grid labels, IDs, holdings, costs and cycle links must come from persisted records or executed calculations, not narrative reconstruction. Identify input provenance (user confirmation), automatic derivation (labels/IDs/calculations), and fee assumptions separately. Missing dates remain null.
- Extending a single-ETF builder requires parameterizing code, name, execution-ID prefix and supersession text together. Incremental record functions must pass the stored ETF identity through; avoid silently generating another ETF's IDs or name.
- For a newly reconciled ETF, preserve previously reconciled files, save and read back only the new target, then register that exact target with the existing midnight job rather than creating a duplicate schedule. Report coverage precisely; an added target is not proof of first scheduled execution or main-ledger integration.
- Test repeated same-letter cycles using exact buy/sell IDs, not only totals. Protect literal user prices and quantities even when they differ from previous suggestions or standard lot budgets.
- See `references/multi-etf-script-reporting.md` for the 159363 thirteen-trade regression fixture and persistence-reporting boundaries.

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
