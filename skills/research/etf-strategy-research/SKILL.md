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

A credible grid backtest needs adjusted price/dividend handling without double counting, cash and inventory accounting, lots, commissions/minimum charges, spread/slippage, and executable fill assumptions. Daily bars do not reveal whether a day's high or low occurred first; resolve intrabar ambiguity conservatively or use finer data.

Benchmark against buy-and-hold with comparable initial capital and risk allocation, not only a fully invested benchmark. Test multiple start dates and market regimes; report total account returns, maximum drawdown, idle cash, turnover, remaining inventory losses, and parameter sensitivity. If not run, explicitly say no backtest has been performed.

## Delivery

Lead with one preferred candidate or a clear no-fit conclusion, then a short alternative table, dated evidence, bear case, capital/risk illustration, and invalidation conditions. Keep fund suitability distinct from a present buy recommendation. Ask outstanding execution questions in ordinary chat. Never claim guaranteed recovery over a multi-year horizon.

## Grid parameter comparison: box mode vs golden ratio

When a user asks to recompute grid parameters under a different interval convention (e.g. golden ratio instead of swing-high/swing-low box), the comparison must cover **five dimensions**, not just the four numbers shown in the report card:

1. **Bounds** — upper/lower/center/step/grids/span
2. **Current price position** — inside or outside the interval? If outside, the strategy is **unexecutable** regardless of theoretical ROI. Flag this before any profit discussion.
3. **Maximum drawdown** — distance from current price to lower bound. A wider interval looks like more opportunity but means deeper paper losses before the first buy grid fills.
4. **Per-round net profit** — gross spread minus commission (万五免五 = 0.0001 per side, min 1 CNY per leg). With 0.6% spacing on a ~2 CNY ETF, per-round net drops to ~33 CNY on a 6,000 CNY cell — less than half the 1% spacing figure.
5. **Monthly ROI** — monthly net profit ÷ total capital deployed (all cells filled). This is the number that actually answers "what's the return?". Do NOT present raw monthly profit without dividing by capital, because a 9-grid strategy that needs 53k CNY deployed and earns 749/month (1.4% ROI) is objectively worse than a 5-grid strategy needing 29k and earning 1,285/month (4.4% ROI).

### The 0.6% spacing paradox

Smaller spacing does NOT always increase ROI. With 万五免五 commission:
- 1% spacing: ~55.8 CNY net per round on 6,000 CNY cell
- 0.6% spacing: ~32.6 CNY net per round on 6,000 CNY cell
- More grids (9 vs 5) partially compensates, but total monthly net drops from 1,285 to 749
- ROI drops from 4.4% to 1.4% because capital deployed grows faster than profit

**Rule of thumb:** 0.6% spacing is only ROI-positive when the ETF price is below ~3 CNY (so the 1 CNY minimum commission is a smaller fraction of the round-trip gross). Above that threshold, 1% spacing dominates.

### Golden ratio window selection

The `--gold_window` parameter is the dominant driver of whether the golden-ratio strategy is executable:
- **window=30-40**: tight interval, current price often above upper bound → unexecutable
- **window=60-150**: wider interval, current price may fall inside → check before presenting
- **window=150+**: very wide, but lower bound drops far below current price → deep drawdown risk

Always run a sweep across `--gold_window` values before concluding a golden-ratio strategy is unsuitable for the current price. The default 150 may not be the right window for the current price regime.

### Reporting format

When presenting grid parameter comparisons, always include a **status column** (✅ 可操作 / ❌ 价格在上界上方 / ❌ 价格在下界下方) so the user can immediately see which strategies are executable. A strategy that requires waiting for a 6%+ pullback is not comparable to one that can start today.

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
