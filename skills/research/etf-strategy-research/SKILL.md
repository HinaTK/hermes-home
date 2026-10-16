---
name: etf-strategy-research
description: "Use when selecting ETFs or evaluating grid strategies."
version: 0.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [investing, ETFs, grids, risk, research]
    related_skills: [grounded-citations]
---

# ETF Selection and Strategy Research

Select investment instruments against a stated risk budget, then separately assess the proposed trading strategy. A defensible fund choice is not proof that a grid will outperform holding it. This workflow produces research, not automatic orders or a promise of capital protection.

## When to Use

- Choosing a long-term ETF, comparing A-share and Hong Kong instruments, or finding a grid candidate.
- Translating a holding horizon, capital amount, and loss tolerance into an illustrative strategy.
- Reviewing whether a grid's realized gains conceal inventory losses.
- Not a replacement for a requested broad-market or sector-scoring workflow.

## Intake and interaction

For this user, prefer ordinary chat for investment suitability questions. They reported that a clarification card left them unable to enter an answer. If a form returns empty, do not wait indefinitely, repeat the same form, or treat the blank as a user decision: give a normal-text reply and accept free text. This is an interaction fallback, not a claim that the tool is permanently broken.

Collect only information that changes the recommendation: accessible markets and trading channel, capital and currency, horizon, loss tolerance, and whether funds are needed at a fixed date. Distinguish loss from starting capital from peak-to-trough drawdown, and instrument losses from whole-account losses. State provisional assumptions without presenting them as confirmed. Once enough is known, research rather than restarting intake. Broker commissions can be deferred until concrete order sizing.

## Procedure

### 1. Separate three questions

1. Is the underlying suitable to own through a downturn?
2. Is valuation and the present market regime compatible with entry?
3. Does the grid improve outcomes after costs versus a comparable passive allocation?

Give separate confidence levels. Missing live quotes or backtests should downgrade entry/strategy certainty without blocking an explicitly preliminary instrument shortlist.

### 2. Verify instrument identity and economics

Use issuer, exchange, and index-provider documents. For each shortlisted fund verify:
- Exact name, ticker, listing venue, underlying index, and document date.
- Constituent count, sector and top-holding concentration, index weighting/rebalance rules.
- Management/custody charges versus other fund expenses versus broker commissions.
- Current liquidity, bid-ask spread, premium/discount, lot size, settlement/same-day sale constraints when giving executable instructions.
- Trading channel, currency exposure, and applicable taxes/fees for cross-border products; do not assume direct Hong Kong access and Stock Connect are equivalent.

Use dated factsheets for structural analysis, never as a live quote. Dividend yield is not a promised fund payout. Low volatility is not capital protection, and low valuation is not proof of undervaluation. More constituents alone does not establish better risk-adjusted performance.

### 3. Rank for the actual objective

For long-term grids, prioritize survivable inventory, diversification, trading frictions, and sustainable fund operation over the largest price swings. Compare a broad-market fund, a defensive/factor alternative, and a cross-market option only where accessible. Explain the strongest reason against the preferred instrument. Do not permanently hard-code a ticker from an earlier recommendation.

### 4. Define risk before grid geometry

Partition initial inventory, finite grid reserve, and cash excluded from further averaging down. Define both a capital-deployment ceiling and, where needed, a market-value exposure ceiling; these are not interchangeable after market moves.

Compute scenarios using tools. Label a static stock/cash shock as a static illustration, not an executed grid simulation or maximum-drawdown bound. Include a scenario that breaches the user's risk tolerance. Explain that cash reduces exposure but cannot guarantee a hard floor, and stop orders can fail to protect against gaps or poor execution.

Distinguish mean-reverting, sustained bear, sustained bull, and low-volatility paths. State inventory risk, selling winners too early, cash drag, and opportunity cost. Do not extrapolate one profitable round trip into annual yield.

### 5. Specify a candidate strategy without pretending it is optimized

If exact parameters are requested, define reference price and timestamp, arithmetic/geometric spacing, buy sizes, sell quantities, core holding rules, total reserve, order eligibility, lower/upper boundary behavior, and reset policy. For preliminary proposals, label all spacing and allocation choices as illustrative assumptions.

No doubling or unlimited downward resets. Include suspending purchases, reducing risk, and reassessing the thesis. Check cash and sellable shares, partial fills, trading-session restrictions, and corporate actions before execution. Ex-dividend price changes must not trigger false economic signals. If money is required at a fixed date, plan risk reduction before that date rather than assuming recovery by maturity.

### 6. Validate strategy claims before upgrading confidence

A credible grid backtest needs adjusted price/dividend handling without double counting, cash and inventory accounting, lots, commissions/minimum charges, spread/slippage, and executable fill assumptions. Daily bars do not reveal whether a day's high or low occurred first; resolve intrabar ambiguity conservatively or use finer data. For this user's repo, first inspect `tools/etf_research/grid_model.py` **and its caller** `tools/etf_research/engine.py` before adapting an existing simulation: the caller may hard-code gap and the model may assume different core lots, initial cash, T+1 settlement and per-lot budgets. An isolated research driver with targeted tests is preferable to changing active trading/ledger code. Distinguish a screener's threshold-day count from matched completed cycles. If the user posits buying every daily low then selling every daily high, acknowledge the hypothetical ex-post upper bound, then explain why a 1% actual grid may not capture it.

For a proposed broker condition order, inspect the user's actual screenshot field by field. A configured price interval and per-trigger amount do **not** establish a total committed-capital ceiling: verify a maximum-inventory control separately. Reconcile starting shares and broker pending orders; semi-auto alerts require human response, and next-bar simulated IOC fills do not reproduce that behavior. Fix when box/anchor parameters were chosen: applying newly selected levels to earlier data is hindsight sensitivity, not prospective validation. Report event-level trades, realized cycles, open inventory P&L, account return, peak deployment, drawdown, blocked/cancelled signals and data window. If only one lot deployed, do not claim the model stress-tested a five-lot inventory or a lower-box break. See `references/grid-backtest-pitfalls.md`.

Benchmark against buy-and-hold with comparable initial capital and risk allocation, not only a fully invested benchmark. Test multiple start dates and market regimes; report total account returns, maximum drawdown, idle cash, turnover, remaining inventory losses, and parameter sensitivity. If not run, explicitly say no backtest has been performed.

## Delivery

Lead with one preferred candidate or a clear no-fit conclusion, then a short alternative table, dated evidence, bear case, capital/risk illustration, and invalidation conditions. Keep fund suitability distinct from a present buy recommendation. Ask outstanding execution questions in ordinary chat. Never claim guaranteed recovery over a multi-year horizon.

## Grid parameter comparison: box mode vs golden ratio

When a user asks to recompute grid parameters under a different interval convention (e.g. golden ratio instead of swing-high/swing-low box), the comparison must cover **five dimensions**, not just the four numbers shown in the report card:

1. **Bounds** — upper/lower/center/step/grids/span
2. **Current price position** — inside or outside the interval? If outside, the strategy is **unexecutable** regardless of theoretical ROI. Flag this before any profit discussion.
3. **Maximum drawdown** — distance from current price to lower bound. A wider interval looks like more opportunity but means deeper paper losses before the first buy grid fills.
4. **Per-round net profit** — gross spread minus commission (万一/0.0001 per side, with the user's confirmed 1 CNY per-leg minimum), board-lot rounding and modeled slippage. This is a conditional single completed-cycle spread, not a realized number of cycles.
5. **Return denominator** — state whether return uses starting account equity, maximum committed capital or time-weighted deployed capital; show them separately when relevant. A static "all cells filled" budget is not necessarily an app-enforced cap and is not a measured return. Do not quote monthly ROI without a chronological, cash-and-inventory-aware simulation or actual matched fills.

### Historical monthly ROI warning

The illustrative monthly ROI and per-month profits above were computed by equating daily high-low range threshold days with completed buy-then-sell trades. That inference is invalid; those percentages are retracted, and must not be reused as forecasts or empirical strategy comparisons. Inspect chronological trade events, broker fill rules, inventory and cash before discussing monthly returns. A daily high-low range is at best an ex-post perfect-timing spread, and may not even cover the chosen 1% grid step. Do not generalize one fund-price threshold into a claim that one spacing dominates another.

### Comparing 0.6% with 1% spacing

A narrower grid lowers gross spread per completed round and may increase the number of opportunities; neither the number of realized cycles nor return follows from daily range counts. Compare both spacings under identical initial cash/holdings, per-cell budget, cumulative inventory cap, fees (万一/0.0001 per side and the user's 1 CNY minimum where applicable), execution rules and market window. Report realized completed cycles, remaining inventory P&L, equity and max drawdown separately. There is **no universal price threshold** below or above which one gap necessarily dominates.

### Golden ratio window selection

The `--gold_window` parameter is the dominant driver of whether the golden-ratio strategy is executable:
- **window=30-40**: tight interval, current price often above upper bound → unexecutable
- **window=60-150**: wider interval, current price may fall inside → check before presenting
- **window=150+**: very wide, but lower bound drops far below current price → deep drawdown risk

Always run a sweep across `--gold_window` values before concluding a golden-ratio strategy is unsuitable for the current price. The default 150 may not be the right window for the current price regime.

### Reporting format

When presenting grid parameter comparisons, always include a **status column** (✅ 可操作 / ❌ 价格在上界上方 / ❌ 价格在下界下方) so the user can immediately see which strategies are executable. A strategy that requires waiting for a 6%+ pullback is not comparable to one that can start today.

## Ranking axis discipline (user correction, 2026-10-16)

When this user asks for a **排名 / 前10** in a grid round-trip context, they mean **完整往返次数（full_cycles）从高到低** — not a composite score. Delivering a weighted-score table and calling it "前10" is a format failure even when the score table is technically correct.

**Rules:**

1. **Default ranking axis = `full_cycles` descending.** Tie-break by `full_cycle_net` descending, then by code. Do not sort by `score` unless the user explicitly asks for a composite view.
2. **Never present a composite-score table as THE ranking without a label.** If you show `score`, put it in a separately titled block (e.g. 「综合评分榜（非往返次数榜）」) and state the axis explicitly.
3. **State the axis before the table:** window, sessions, universe size, eligible rows, failed windows, and whether current holdings are included or excluded. A number without this context is not actionable.
4. **Include current holdings in the ranking unless the user asks for a non-holding-only view.** Excluding holdings silently turns a full-pool ranking into a filtered one.
5. **Do not let an empty `rotation_top10` go unexplained.** If the report's round-trip top-10 block is blank while `ranking` has data, say so and recompute the round-trip top-10 from `result['ranking']` directly rather than trusting the precomputed block.
6. **Never reuse a score table's position to imply a round-trip rank.** A composite #1 with 22 cycles is not the round-trip #1; state both numbers.

See `references/ranking-axis-discipline.md` for the 2026-10-16 failure transcript and the exact recomputation command.

## Period summary format (user requirement, 2026-10-16)

When producing a 「二、合计」 / period summary for this user, always include:

- **交易天数** — count of trading days in the period, computed from the stated start date, not from how many distinct trade dates happen to be recorded in the ledger.
- **本金 / 净投入** — cumulative net cash outflow (sum of buy amounts − sum of sell amounts + all commissions), per ETF and in total.
- **固定起始日** — the user anchors periods at a specific date (currently 2026-09-23). Confirm the start date with the user rather than deriving it from the earliest recorded trade; earlier trades with `date: null` must stay null, never backfilled.
- **做T累计净利** — per ETF and in total, with round count.
- **口径声明** — state that net invested is cumulative net cash flow, not current 占用; that commissions are locally estimated (万一, 1 CNY minimum per leg) and not broker-confirmed; and that account cash / frozen shares / pending orders remain unreconciled.

## Evidence checks

Use grounded-citations for source mapping, but manually inspect each material financial claim. A validator's green status is not proof that the quote supports the number, that table columns were read correctly, or that dates are current. See [financial evidence and grid illustrations](references/financial-evidence-and-grid-illustrations.md) for extraction checks and reusable counterexamples.

## Verification checklist

- User constraints, assumptions, and unresolved questions clearly separated.
- Tickers, fees, index data and dates verified from documents, not search snippets alone.
- Allocation and scenario arithmetic actually computed.
- No static stress test mislabeled as a path-dependent grid backtest.
- No annual volatility mislabeled maximum drawdown; no dividend yield mislabeled payout.
- Bear case, failure triggers, and a risk-budget breach scenario included.
- Live-data or simulation gaps explicitly disclosed.
- Final conclusion does not overstate what was verified.
