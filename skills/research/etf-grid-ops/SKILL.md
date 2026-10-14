---
name: etf-grid-ops
description: "Use when sending A-share ETF grid tickets or fills."
---
# A-share ETF grid live ops

## Current confirmed-state migration (2026-10-14)
For 589720 and 159363, authoritative trades are ONLY `cache/grid-account/confirmed-589720.json` and `confirmed-159363.json`, not legacy ledger.json/tickets. Actual runtime entrypoints must be verified from installed launchers/--help, never assumed deployed from source edits alone. Never call legacy whole-ticket apply or bare 成功. Inputs require explicit fill identity/details; preserved historical dates remain null. Persist qty, sellable_qty and max_grid; daily00:01 writes sellable=qty, same-day rerun idempotent. 1.5% current grid, budgets8000/6000, A–Z stack max pointer; one buy and one sell; no broker execution authorization. Intraday cron is now every minute with trading-session gate, day high/low/spot unified dedup, not minute bars. 159992 remains unreconciled: do not infer its holdings or account cash from broken old ledger. Old parameters, paths and frozen playbook below are HISTORICAL and cannot override these newer user instructions. Follow etf-grid-maintenance stateful/persistence safeguards and report deployed integration vs tests separately.


Research (universe, backtest, ranking) belongs in `etf-grid-research`. This skill is the **live ticket** path: what the user can execute today, at what clock, from which quote.

If both are relevant, load this one for anything that looks like an order, limit, lot size, or “今日操作”.

## Clock (do not invent fills before continuous trading)

A-share cash session:

| Clock (Beijing) | What it is | Ticket |
|---|---|---|
| before 09:15 | pre-auction; last is usually **yesterday close** | preview only |
| 09:15–09:25 | call auction; 09:25 match | still not a resting continuous fill |
| 09:30 | continuous trading opens | first moment a live last can be an executable limit |
| 09:31 | ops send | **executable only if same-day 09:30+ vendor quote has arrived**; otherwise downgrade to 勿下单 preview |

**User correction (keep):** a 09:10 “build suggestion” cannot guarantee the suggested price. 09:10 is before auction even starts. Do not lock limit prices then. Do not tell the user to buy at that print.

Tencent `qt.gtimg.cn` field ~30 is the quote timestamp (`YYYYMMDDHHMMSS`). Treat the quote as live only if it is **today and HHMM ≥ 0930**. If an execute job fires but the stamp is still pre-0930, **fall back to preview** — do not lock yesterday close as a limit.

Details: `references/a-share-session-clock.md`.

## Ticket contract

Grid jobs use `no_agent` script stdout. As of 2026-09-28, deliver to the user's Feishu DM `oc_7d2d8ab5d54051067f8e0cd228652133` (not WeChat; iLink sends repeatedly failed):

- 09:10 **preview** — `scripts/grid_weixin_preview.py`. Header `【预告】`. Actions empty. “勿下单”. Cron `bba8cc3c5333` now `deliver=local` (user 2026-09-30: no Feishu preview noise); still runs and saves local output, never broker execution.
- 09:31 **execute** — `scripts/grid_weixin_execute.py`. Header `【操作】` only after same-day 09:30+ quote; stale/auction quote downgrades to preview/勿下单. Cron `e01b833b150d`.
- every 10m **intraday** — `scripts/grid_weixin_intraday.py`. Cron `ef9a27327990`, Feishu DM. Empty stdout means no alert was generated, not necessarily a failed run. Script returns unless 09:35–14:57 on a session day with a live quote. Schedule `*/10 * * * 1-5` is fixed on :00/:10/:20/:30/:40/:50; script's 09:35–14:57 session gate makes 09:40 the first normal intraday check on trading days. User 2026-09-30 explicitly reverted the minute-bar experiment: monitor pending limits with the original Tencent **day-to-date high/low** (~33/~34) and spot fallback. No minute-feed requests, no 30-minute window, no ticket-time or first-observation cutoff. The user accepts historical-extrema false reminders to avoid excluding brief touches via time filtering. Say “今日最高/最低” and explicitly warn “可能发生在建议挂单之前”; this is a prompt to check 银河, never proof of a new post-order touch or fill. Persist one-shot dedup by code, side, level, and trading day. Day-extrema and current-spot touches now use ONE `trend_alert` path and the same persisted `alerts` map: after an extrema reminder, a later spot crossing must remain silent for that code/side/price. The old separate `fill_alert` / whole-ticket `fill_alerted` notification path is removed, so one reminded action does not suppress unreminded different levels. Missing extrema use current spot (including a first observed touch) with evidence labeled `现价`, not an invented day high/low. Preserve existing same-day alerts even if the ticket/action fingerprint or former monitor version changes, and reset only on the next session. **Same-day re-entry caveat:** previously alerted same-price replacement orders are not re-armed from cumulative extrema. Repeat touches and provider outages can still be missed; never promise zero misses. The 09:31/10-minute schedule, grid gap, core inventory and EOD policy remain unchanged. Do not auto-book. For diagnosis compare cron `last_run_at`/status, saved output (silent vs alert), active ticket, trend-state file, and live quote timestamp/high/low. See `references/intraday-extrema-monitor.md`.

Ledger: `HERMES_HOME/cache/grid-account/`. Preview status must not be `apply()`-able. A **pending** execute ticket is locked until `成功`/`失败`, except when a confirmed partial fill makes it stale; archive/replan in that case. After a booked sell, emit a same-day **rebuy** ticket (same qty, limit = sell/1.02, do not chase).

Core modules: `HERMES_HOME/scripts/grid_account.py`, `grid_weixin_ops.py`, `grid_weixin_confirm.py` (`成功`/`失败`), `grid_weixin_intraday.py`.

Fill confirm: user replies in **Feishu DM** (or any Hermes chat). For a ticket with multiple orders, require code + side + quantity + actual execution price before booking a fill; a bare `成功` is ambiguous and must NOT invoke `grid_weixin_confirm.py` (it books the whole ticket). Book once; verify ledger and active ticket. **After every uniquely confirmed fill**, promptly acknowledge what was booked and regenerate the next actionable ticket from the refreshed ledger, active ticket, pooled T+1-eligible inventory, and broker-resting order reservations; do not stop at a P&L/holdings summary. When the user reports the *same code, side, quantity, price* again on the same trading day after an intervening opposite fill, do not automatically dedupe or book: it may be a second completed cycle. Check ordered fill history and, if the wording cannot distinguish repeat from new execution, ask the one essential clarification before writing. An unanswered/interrupted clarification leaves the ledger unchanged; explain the pause plainly and resume when answered. When a same-day sell of a recently bought grid is funded by older eligible inventory, never simply retire the ineligible new lot: separately reconcile settled-share depletion and cost basis, and flag any already-written ledger that used the shortcut before posting another ticket.

**Partial-sell reconciliation pitfall:** the ticket's grid letter names the *target price*, while T+1 checks the pooled sellable inventory. When an explicitly named target grid is itself T+1-eligible and fully sold, retire that grid's ledger quantity (and allocated purchase cost/fee), rather than always consuming the oldest A-lot: doing the latter leaves the sold C-grid active and reissues its sell recommendation. If selling a target grid bought today using older T+1 inventory, track pooled settlement separately; do not simply retire the ineligible lot and overstate remaining sellable shares. Record actual sell price and an explicitly provisional fee, compute proceeds and realized P&L from that retired inventory, and leave other ticket actions unfilled. Archive the old ticket; keep known resting buys, and mark any new sell/rebuy rows as *suggestions*, not broker-confirmed orders. Rebuy uses executed sell price / (1 + gap), staged below without chasing. Make the pending-ticket staleness check recognize an existing rebuy and its separately staged lower buy so a refresh does not silently discard either. After a sell at a better/worse actual execution than the theoretical grid, derive the *next lower staged level* from `actual sell / (1+gap)` and then another gap below that rebuy, rather than from the older surviving lot's price. On new-ticket generation, rebuy must not `continue` past the nearest sell and lower staged buy; reserve its cash and cap usage before sizing the lower buy, and give the rebuy a distinct lot ID (e.g. `D-rebuy`) so it cannot collide with staged `E`. Test both a pending-ticket refresh and a new-day ticket with isolated ledger/ticket paths; compare real-ledger checksum before/after tests to catch accidental test writes. See `references/partial-fill-reconciliation.md`. **Partial rebuy confirmation:** book only the named buy (actual qty/price and provisional fee), clear its rebuy obligation, append a same-day T+1-ineligible lot, and preserve unrelated pending lower buys. Before replacing a farther sell with the rebought grid's nearer sell target, sum *all* broker-resting sell quantities against the old T+1 pool; archive/replan the stale ticket, but never imply the old broker sell was actually cancelled or the new sell was placed. Dry-run the refresh against a temporary ticket copy, then read back the exact ledger/history/active ticket; see `references/same-day-rebuy-reconciliation.md`.

## Frozen playbook (do not reverse unprompted)

Until the user explicitly changes it:

- 10万 RMB trial, GAP 2%. User on 2026-09-30 authorized a gradual **159992 -> 589720** migration during the monthly observation period; retain **159363**. Third ETF selection is research only, not a buy authorization. `cache/grid-account/migration.json` is the live exit-only guard: source stops new buys/rebuys, target buys are still disabled pending broker reconciliation. Do not mistake a local recommendation removal for a broker cancellation or rewrite holdings before actual fills.
- Two-day build: day-2 **only completes the second half**; do not sell the first lot because T+1 unlocked.
- Grid sells only after the initial two-day build is complete; after that, prioritize turnover rather than mechanically waiting for the newest buy lot to unlock.
- User revised the account allocation: cost caps 159992=4.6万 / 159363=3.4万 (约8万 total); 10万账户内 cash floor 2万, 账户外约8万保护金不进本账. Per new down-grid lot budgets ~8000/6000; GAP 2%.
- Maintain each ETF as a total T+1-available inventory pool, not as isolated buy lots. A new same-day buy cannot be sold, but its grid sell target may be placed immediately using older T+1-available shares, provided the pool covers the quantity and no other sell order reserves those shares. Use the newest/lowest filled grid's +2% target for the next turnover sell; do not retain a farther B/A sell if it would consume the pool needed for the nearer D/C turnover. Example: after 159363 D 5100@1.169 fills, replace B 4700@1.298 with D 5100@1.192, then stage E buy 5200@1.146.
- Down-grid adds are dynamic, not capped at one per calendar day: if the live price has crossed several successive grid levels, stage each crossed level, subject to cash floor, per-ETF cost cap, and a hard maximum of 12 staged levels per ticket. Each level must be independently checked against existing pending orders; no duplicate orders. An execution can be better than the limit: book actual confirmed quantity and execution price, not the order limit. With several orders on a ticket, never call `grid_weixin_confirm.py 成功` for one fill: it applies ALL actions. Book only the identified action, archive/replan the ticket, and verify both ledger and active ticket. User may report code+side+quantity+price.

## Authorized gradual migration (2026-09-30)

`grid_migration.py` + `cache/grid-account/migration.json` guard the existing planner, renderer, intraday extrema path and EOD notes. Source `sz159992` is EXIT-ONLY: no newly planned buys or rebuys, and source sales no longer generate rebuy obligations. Legacy source buys remain in historical tickets/ledger for reconciliation; the guard removes them from current suggestions and retains `withdrawal_actions`, never asserts broker cancellation. Initially verify old source buys 9,400@0.846 and 9,600@0.829; if filled, book reality before replanning. Source participation core may be exited because the user explicitly authorized complete replacement, while the 159363 core remains unchanged. Retire a named, T+1-eligible migration sell lot before older lots so a sold B-grid is not reissued. Block ambiguous whole-ticket success when multiple actions remain. Target `sh589720` buys remain disabled until old orders, funds and fresh target execution checks are reconciled; this is not completed migration and is not yet an automatic target grid. Proposed seed 8,000 split into two 4,000 tranches is a plan, not an order. Old/new innovation-drug holdings share original 46,000 cap, 159363 retains 34,000 cap, 20,000 cash floor and external protection cash remain untouched. Do not activate a third ETF merely because research selected it. Keep actual holdings, history and reminder state unchanged during research and test in temporary paths. Regression suite included 42 tests at this check; broker delivery and fills are separate verification.

## Parameter questions and one-way markets

When asked to change gap, separate **per-cycle spread**, **completed cycle count**, **total realized net spread**, and **account return including unsold inventory**. Wider gaps do not guarantee higher aggregate profit: check both names and recent windows using the same backtest model, disclose its fill/lookahead and sizing differences, and do not alter scripts, pending tickets, or broker-facing limits merely because a hypothetical gap was discussed. If user decides to keep the gap, leave it unchanged. A later switch needs explicit treatment of existing lots' sell targets, rebuys, outstanding buys/sells, and effective date; reconcile broker orders first.

Distinguish three different limits when answering “how many grids?”: per-name invested-cost caps, shared cash floor, and the maximum *staged levels per ticket* (not a lifetime position count). Per-grid budgets are chosen sizing heuristics, not optimized returns; show how 100-share rounding and provisional fees turn a budget into actual order size. On new funding, do not mechanically multiply lot size or treat external protection cash as deposited: confirm added capital and resting orders, set cash/risk budget and per-name caps first, stress-test correlated holdings, then stage extra capacity. Keep the current gap unless explicitly changed.

For a persistent one-way rise, the live grid **does not automatically ratchet the anchor upward**: sell tradable inventory at existing targets and stage rebuy at actual sale price/(1+gap) without chasing. Since the 2026-09-29 core amendment, `grid_account.py` limits NEW sell recommendations to leave at least 159992=9,100 and 159363=4,600 total shares as a participation core (not specific tax lots). The core prevents *new local recommendations* from zeroing each ETF but does not cancel broker-resting old sells, insure against drawdown, or guarantee profit. A long rise still leaves most cash idle. A confirmed legacy sell breaching the floor must still be booked accurately and flagged. Never imply the broker order was cancelled; reconcile outstanding orders before following new tickets. Rebase remains advisory, never automatic.

## 收盘单边上涨复核（试运行，非自动上移）

`grid_eod_decision.py` 每交易日 15:20 在飞书运行（cron `b3097b45fafa`），先检查两只 ETF 的当日收盘报价时间、日线日期及收盘价一致性，保存 `cache/grid-account/eod/YYYY-MM-DD.json`，以次一交易日为有效期。09:10 本地静默预告及 09:31 飞书操作单由 `grid_weixin_ops.with_evening_review` 附加非执行备注；若收盘后有新成交入账，旧备注失效。盘中/休市不生成有效报告。

2026-09-29 修订后候选门槛：该 ETF 剩余份额不超过参与底仓+约一格（按收盘价和当格预算测算）、已有用户确认卖出且其后未确认接回或新增买入、**单次收盘**高于最后确认卖价2%、收盘高于走升的20日均线，且未高出该均线8%以上。账内仍有未接回记录时也可提示人工复核，但旧接回记录和银河在途买单不会自动撤销；不可叠加新买。满足时显示“低库存上移候选”和收盘回落2%的观察价；这是**未经专项回测验证的试运行阈值**，不是自动交易信号。旧版连续3收盘/高卖价4%门槛已撤下，旧收盘报告的`policy_version`不匹配时晨间标记失效。永不自动抬高现有目标价、撤券商委托、补买/记账或改2%间距。任何候选在下一交易日必须重新核对银河在途单、成交、可用资金和实时行情；不因观察价触及就推定成交。数据异常只报错，不生成看似有效的价位。

## Output shape (Feishu)

**User-confirmed Feishu ticket format:** headline `**现在的剩余操作建议**`; per ETF a bold `**代码 中文名称**` heading, then bullet rows with actual grid letters and bold comma-grouped quantity/price, e.g. `- 卖 C 格：**9,400 份 @ 0.863**` and `- 买 D 格：**9,600 份 @ 0.829**`. The example letters/numbers are formatting fixtures, not live recommendations; derive real rows from current ledger, pending ticket and available pool. Keep the 09:10 preview visibly a preview/勿下单; do not reprint an active execute ticket as an executable 09:10 action. Label quotes as `昨收/盘前` vs `实时`. Never imply a preview price or intraday touch is a fill. Not financial advice; do not cite backtest PnL as today’s money.

Before sending any ticket, run a preflight checklist: (1) reconcile the latest user-confirmed partial fills; (2) compare active ticket actions with broker-facing intent; (3) ensure a filled lower grid has both its nearest +2% sell target and the next lower buy target; (4) ensure sell quantities do not exceed the total T+1-available pool after other resting sells; (5) do not describe an already-resting order as “暂不挂”。 If a user corrects an order, acknowledge the exact mistake and regenerate the full remaining ticket rather than explaining the old logic first.

**User correction — names:** every ticker line must be `code + Chinese product name`, never the six-digit code alone. Current book: `159992 创新药ETF银华`, `159363 创业板人工智能ETF华宝` (`NAMES` in `grid_account.py`).

**User correction — newlines:** WeChat ilink **collapses a single `\n` into a space**. Tickets that `"\n".join(lines)` arrive as one wrapping paragraph. Join rows with **`\n\n`** (blank line between each row). Do not “fix” this by adding markdown or tables.

Cron `deliver=weixin:...` still wraps **Cronjob Response** header and “To stop or manage this job” footer. That chrome cannot be stripped from the job; do not spend turns trying. Body spacing is the part we control.

Do **not** attach `etf-grid-research` to the live WeChat cron. That skill dump makes tickets long and slow.

**行情数据字段说明（qt.gtimg.cn）** 腾讯行情 `qt.gtimg.cn/q=XXXXXX` 返回的字段顺序（在时间戳后）依次为：涨幅（元）、涨幅幅度（%）、今日最高价、今日最低价、**当前价（收盘价/现价）**。务必使用当前价字段进行市值和盈亏计算，并在汇总时标明确切获取时间戳（如 `20261008161457`）。不得将最高价、最低价或成交量字段误认为当前价。

**费用规则说明** 自 2026-09-30 起，用户确认网格交易佣金为“万一免五”（成交额0.01%，无每笔最低5元），即每笔买卖费用 = max(成交额 × 0.0001, 1.0) 元。所有历史记录及现金、持仓成本均应按此规则重算。

**单挂原则（已在账户汇总部分强调）** 同一只ETF同一时刻只保留一个买单和一个卖单，其余挂单必须同步取消。买单选择最近的有效接回价；卖单选择最近的有效卖出目标价。此规则适用于操作单生成与挂单建议，仅影响下单执行，不改变持仓成本的历史演算。
**行情数据字段说明（qt.gtimg.cn）** 腾讯行情 `qt.gtimg.cn/q=XXXXXX` 返回的字段顺序（在时间戳后）依次为：涨幅（元）、涨幅幅度（%）、今日最高价、今日最低价、**当前价（收盘价/现价）**。务必使用当前价字段进行市值和盈亏计算，并在汇总时标明确切获取时间戳（如 `20261008161457`）。不得将最高价、最低价或成交量字段误认为当前价。

**费用规则说明** 自 2026-09-30 起，用户确认网格交易佣金为“万一免五”（成交额0.01%，无每笔最低5元），即每笔买卖费用 = max(成交额 × 0.0001, 1.0) 元。所有历史记录及现金、持仓成本均应按此规则重算。

**单挂原则（已在账户汇总部分强调）** 同一只ETF同一时刻只保留一个买单和一个卖单，其余挂单必须同步取消。买单选择最近的有效接回价；卖单选择最近的有效卖出目标价。此规则适用于操作单生成与挂单建议，仅影响下单执行，不改变持仓成本的历史演算。
## 账户汇总与成交账本对账

**用户纠正——逐笔成本而非只报期末：**当用户要“从建仓到每一次成交后持仓还有成本”，先按账本 `history` 的实际成交顺序筛选该 ETF，逐笔列日期、买卖/份额/实际价、成交额、买卖费、成交后份额、累计净投入和每份摊薄成本。不能用期末份额倒推中间交易，也不能把票据目标当成交。用 Decimal 或程序逐笔验算，买入净投入增加 `数量×成交价+买费`，卖出净投入减少 `数量×成交价−卖费`；每步份额相应增减，摊薄成本=`累计净投入/剩余份额`（份额为零时不计算）。该指标是**将历次卖出净款冲减累计投入的现金回收口径**，可能接近券商显示的成本价，但券商具体算法、逐笔实际佣金及价格时间必须独立核对；不得因数值恰好吻合就宣称已验证券商算法。另列库存原始成本、按卖出库存结转的已实现盈亏，避免把这两种成本混叫“持仓成本”。历史账若暂估最低5元、用户现行规则最低1元，须并列原账口径与按现规则重算的**模拟口径**，注明未经交割单确认，不静默改写历史成交、现金或批次。具体复盘案例见 `references/position-cost-reconciliation.md`。

用户要求“汇总交易情况”时，**先给持仓和成本**，不要用策略概述、网格价差或迁移计划代替账户报表。先读活动账本、当日票据和最新用户确认的成交；逐笔将确认成交与账本 `history` 对照（代码、方向、数量、实际均价、日期），尤其检查用户已确认但只写入记忆/一次性脚本、尚未真正运行入账的买单。只在确认唯一且未入账、成交细节完整时做一次安全入账，备份并读回精确目标；如果重复成交含义不清则询问，不伪造持仓。算术用工具，验证每只 `qty` 与正份额 lot 总和、`cost_cash` 与现金变动、日期及 T+1 可卖池；明确活动票据只是建议，券商委托未知。

汇总表至少列：代码＋中文名、持仓份额、持仓成本总额（标明是否含暂估买入费）、加权单位成本＝持仓成本/份额、逐批成交价与数量、账户现金、每只/共享成本上限及余量。可附估值时，盘后查询的供应商“最后价”要标出**行情自身时间戳和查询时刻**，绝不能冒充当前实时价或已验证的交易所收盘价；按每只价格计算市值和浮盈亏后，再算账户现金＋市值。把**按真实可卖库存成本结转的已实现盈亏**、未售持仓浮盈亏、网格买卖价差（现金周转指标）分开，尤其当今日新格卖目标由旧 T+1 库存覆盖时，不能把新格价差称作该库存的已实现利润。旧账佣金口径与用户现行费率不符时披露混用和交割单待核，不把暂估均价伪装成银河成本；若账本有待修复的期末现金/持仓不一致，先标记并核清，再发布合计。后续操作建议另列，避免挤掉用户要的成本汇总。详见 `references/grid-account-summary-checklist.md`.

**用户强制——实时行价与时间戳：**所有市价引用必须标明确切获取时间（如腾讯行情 `qt.gtimg.cn` 的 `YYYYMMDDHHMMSS` 时间戳），不得沿用缓存或过时报价。若用户追问“现在几点、你拿的数据是什么时候的”，必须立即用当前实时数据重新汇总修正，不做辩解。持仓盈亏、市值计算均基于此实时价。

**用户强制——单挂原则：**同一只ETF同一时刻**只保留一个买单和一个卖单**，其余挂单**必须同步取消**。买单选择最近的有效接回价；卖单选择最近的有效卖出目标价。此规则适用于操作单生成与挂单建议，仅影响下单执行，不改变持仓成本的历史演算。

## Ledger vs broker

The live book is `HERMES_HOME/cache/grid-account/ledger.json`, not 银河. User may confirm via Feishu/another chat. A bare `成功` / `失败` is **not** enough to book a multi-order ticket: obtain the specific code, side, actual filled quantity and execution price first. `apply()` on the whole ticket would otherwise book unrelated orders. Verify ledger and active ticket after the identified fill; hanging orders and touched prices are not fills. For an explicit cost correction, update the affected lot and recompute cash/target consistently.

**User correction — T+1 ≠ sell:** “有了可卖库存” means day-2 can *complete the second buy* because the first lot has settled. It is **not** an instruction to sell the first lot. While `second_pending` > 0, tickets may only **buy the remainder**, never grid-sell.
