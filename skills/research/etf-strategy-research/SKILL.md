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

## Cross-border (QDII) entry analysis (2026-10-24)

### Premium freshness pitfall

Never compute a QDII ETF's premium from a stale NAV. Cross-border NAVs publish after the A-share close and lag the overseas session; when the underlying moved sharply, a day-old NAV can flip the premium's sign (159866 on 2026-10-22: stale prior-day NAV implied −0.05% "premium normalized"; the fresh same-day NAV showed +2.35% after Tokyo fell ~2.4%). Always print the NAV date next to the premium, and re-derive the premium immediately before acting on any premium-based trigger.

### Structural premium: never gate entry on premium normalization

Before using premium as an entry gate, compute its distribution over ≥100 aligned NAV days (mean, median, current percentile, % days >2%, % discount days). For structurally premium products — QDII with exhausted quota (159866: 79% of days above +2%, median +2.36%, discount on ~1% of days) — "wait for premium ≤ 0" is an infinite wait. Use premium only for:
1. **Same-index vehicle selection** — lowest premium + highest liquidity among ALL funds tracking the same index (159866 vs 513520/513000/513880), including a full comparison table before choosing;
2. **Extreme-risk alert** — >5% premium: do not buy.
Entry timing itself rests on price/structure signals, not premium normalization.

### Regime and entry-timing toolkit

When asked "is now a good time to buy" or "bull or bear, any signs":
- Run the **four-signal regime check**: ① MA50 vs MA200 + price vs MA200 (bull framework intact?); ② higher-high/higher-low pivot structure (divergent = converging triangle, direction pending); ③ drawdown band from 250-day high (0~−10% high zone / −10~−20% correction / −20~−35% bear / deeper = deep bear; −20% is the classic dividing line); ④ 20-day realized vol vs its own median (spike = bear-start signature). Present as a signal table; when signals split, say so — that IS the answer, don't force a verdict.
- For left-vs-right entry questions, run a **forward-return event study** on the fund's own history: left = close below MA20 by ≥3% while falling; right = MA20 reclaim day. Report mean/median/worst return, win rate, and path max-drawdown at 20 and 60 sessions — and disclose the sample's regime bias (a bull-market sample inflates left-side win rates; the left side's true uncovered risk is a trend that never comes back).
- Give concrete invalidation levels (e.g. MA200 ≈ price −2% → cut early rather than ride to a −25% stop).

See `references/qdii-premium-and-entry-timing.md` for the 2026-10-24 159866 case numbers and reproduction script.

### Fresh skill-driven re-analysis

When the user says "不要管我的方案，重新用 skill 判断" (ignore the prior plan, re-judge from the skill), run the skill's framework from scratch on current data WITHOUT anchoring to the previously agreed plan, present findings, and only then reconcile the two. A prior plan is a hypothesis to test, not a constraint on the analysis.

## User-intuition rules: validate before adopting (2026-10-26)

When the user proposes a trading rule and flags it as intuition without basis (「我的方案只是没有依据的直觉」), or when two of the user's rules conflict, do not merge or implement blindly — validate with data, then decide. Workflow that earned user trust here:

1. **Formalize the claim** into a testable form: state definition, forward window, outcome metric (grid cycles, max drawdown depth, terminal return).
2. **Pooled validation**: per-ETF × per-day samples from the research cache; bucket by rule state and measure forward outcomes. A rule earns adoption only with a monotone, sizable gradient across buckets.
3. **Test refinement variables before adding them**: every proposed sub-cut (ADX stratification, deviation-depth bands, hysteresis thresholds) must itself show a separable gradient on pooled data. Record rejected cuts as rejected — do not re-propose them.
4. **Event-level dual simulation**: from each first-entry-into-state event, simulate rule-on vs rule-off over the same forward window; report win counts, mean vs median delta, tail (P90), and capital-occupation delta. A mean/median split (mean favors the rule, median against) reveals insurance structure — small frequent cost, rare large payoff — and the honest description is "tail insurance", not "return enhancer".
5. **Fix semantics, not behavior, when only the word is wrong**: if the action survives validation but the label overstates (39% of "banned" events were profitable afterward → 禁入/ban is wrong), rename the label (暂停买入/pause) with the release condition stated, and change zero behavior.
6. **Disclose data-derived vs engineering-chosen parameters separately**; thresholds calibrated on one regime's sample are readings, not eternal truths. Also disclose coarseness: close-price-path cycle counts are approximate; only gradient direction is reliable.
7. **Question the question before validating it** (2026-10-28): when the user asks "why do you think X is the most targeted fix", or challenges the framing itself (「我不认为有任何理论是只根据5线就做判断的，你学投资理论到底学了个啥」), re-derive the answer from the theory framework FIRST, then test it — and report when your own earlier reasoning gets falsified mid-validation (the 道氏123 case: single-name 6-sample "condition ② has discriminative power" was destroyed by the pooled 629-event run). Presenting theory names as citations while shipping a stitch-work indicator combo is a competence failure the user will call out. The fix pattern: theory framework → concrete testable rules → pooled validation → honest retraction of what fails.

Watch for **bucketing artifacts**: an early coarse-bucket run manufactured a spurious "highest output" conclusion that fine 0.25–0.5% cuts destroyed. When a conclusion flips with bucket boundaries, the variable is too noisy to gate on.

See `references/entry-gate-validation-2026-10-26.md` for the full case: unified four-level gate (五线全破暂停买入 > ADX≥25动能暂停 > 试错仓 > 正常), the rejected-variable evidence, the 573-event comparison, and commits 8101603/c0b051e.

### Label-drift TDD pitfall (2026-10-26)

User-facing labels with semantic weight (「禁入」 vs 「暂停买入」) drift silently when no test asserts the human-readable string — internal-code assertions (`verdict == 'no_entry'`) pass through any wording. When renaming or introducing a user-visible term, add a label-text assertion test first (RED on the old wording), then change LABELS (GREEN). Same for rendered-table headers: adding a column requires syncing header-assertion strings in tests within the same commit — a 9-column renderer shipped against an 8-column assertion and failed three commits later.

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

- **交易天数** — count of trading days in the period, computed from the stated start date, not from how many distinct trade dates happen to be recorded in the ledger. **Must exclude A-share market holidays, not just weekends** (see `references/period-summary-format.md` — the first version wrongly reported 18 trading days for 2026-09-23→10-16; the correct count is 11 after removing 中秋 9/25–9/27, 国庆 10/1–10/7, and 10/10). Verify the year's official holiday notice; it changes every year. State which holidays you excluded.
- **本金 / 净投入** — cumulative net cash outflow (sum of buy amounts − sum of sell amounts + all commissions), per ETF and in total.
- **固定起始日** — the user anchors periods at a specific date (currently 2026-09-23). Confirm the start date with the user rather than deriving it from the earliest recorded trade; earlier trades with `date: null` must stay null, never backfilled.
- **做T累计净利** — per ETF and in total, with round count.
- **口径声明** — state that net invested is cumulative net cash flow, not current 占用; that commissions are locally estimated (万一, 1 CNY minimum per leg) and not broker-confirmed; and that account cash / frozen shares / pending orders remain unreconciled.

## Evidence checks

Use grounded-citations for source mapping, but manually inspect each material financial claim. A validator's green status is not proof that the quote supports the number, that table columns were read correctly, or that dates are current. See [financial evidence and grid illustrations](references/financial-evidence-and-grid-illustrations.md) for extraction checks and reusable counterexamples.

## Data-table delivery rule (2026-10-24, hard rule)

**Every data table delivered to this user must be script-rendered and pasted verbatim; a column absent from the script output must never be hand-filled.** Born from a fabricated 近20日往返 column in a TOP10 whose numbers matched no field in the run's data (user: 「一切数据都有依据，落实脚本吗」). Renderers: `entry_rank --render`, `grid_summary.py`, `render_eod()`. Every delivered number is audited across turns. See `references/data-table-delivery-rule.md` for the full rule, the audit method that catches fabrications, and the error history.

## Efficiency-metric comparability (2026-10-26)

When comparing the user's confirmed-fill performance against the research engine's simulated metrics, never compare raw percentages — the two systems use different numerators AND denominators:

- **Per-round yield (单轮收益率)**: ledger = net ÷ that lot's buy amount (≈ gap − fee drag, a grid-geometry constant, NOT a performance metric); engine has no such field, and deriving one via `cycle_net ÷ cycles ÷ avg_cost` divides by the whole capital base (~4x dilution vs the per-lot denominator).
- **Capital turnover (资金周转效率)**: ledger = cumulative T net ÷ CURRENT net invested (point-in-time, conservative for late-scaling grids); engine `cycle_net_per_avg_cost_pct` = window cumulative ÷ TIME-AVERAGE occupation over every 5m bar, over 63 sessions.
- **Only directly comparable metric**: net spread per round in yuan.

Before any "which is higher" statement: (1) normalize by window length (ledger starts 2026-09-23, engine window is 63 sessions — divide both by trading days), (2) normalize the denominator type. After normalization the ledger actually ran ABOVE the engine for 589720/159363 (1.5% gap + 8,000/6,000 lots generate more rounds per oscillation than the engine's 2%/5,000 defaults). See `references/efficiency-metric-definitions.md` in the etf-grid-efficiency-rotation skill for full formulas.

## ADX 梯度×试错仓门控研究（2026-10-27）

用户追问门控规则的数据依据（"ADX三参数怎么用"→"中间态20~25有没有"→"用数据证明"→"现在不能直接跑全池吗"）。研究方法、已否变量（手搓 Wilder 平滑算出 ADX=318 的教训、"X 被放行"类断言必须先沿 gate 代码路径验证）及 321 只全池脚本见 [references/adx-gradient-study-2026-10-27.md](references/adx-gradient-study-2026-10-27.md)。核心纪律：**全池样本落盘并过显著性检验前，不改门控规则**；样本不足时给三盆冷水（薄样本/窗口偏/U 型结论对度量口径敏感），不把趋势预览当结论交付。

## 站稳/巡检信号：候选与裁决（2026-10-28）

现行门控解除条件（收盘站回 5 日线）在全池 629 次事件里 **74% 是假站稳**。用户下令理论先行后定架构：未持仓票三灯资格（结构+量价+时间）管开仓，持仓票 ER+ATR+区间管巡检。裁决结果（勿重提议毙项）：

- **滞后资格原则（最高优先）**：前瞻决策输入必须滞后 ≤1 交易日；ADX（2-3周）/±DI（1-2周）只许事后归因，禁止进决策栏。拿滞后指标给用户做前瞻参考被用户重点批评过。
- **已毙**：ADX 斜率（无分离、方向反）、量能确认（分布重叠；高阈值误杀 85% 真站稳）、道氏123（②守前低全池无效、③当日破前高不可行）、三条件 AND 巡检（暂停 65% 天数瘫痪网格）。
- **唯一幸存解除增强**：连续 2 日站回 MA5（假站稳 74%→64%，召回 100%，代价 1 天）。
- **巡检最优（已落地 06496f3）**：F = 五线全破 **OR ATR5/ATR20>1.15**，全池 +317k vs 现行 +252k；增量 680 次拦截平均每次避损 95.9 元，现行拦而 F 不拦 = 0 天。589720 回放：9-23/24 ATR 先于五线全破触发 — 波动先于价格破位。部署铁律（用户原话「不修改原来代码」）：**F 落地为独立脚本 tools/patrol_f.py**，与生产门控并行、可整体摘除；不在 gate_check 里加条件。禁入语义已改「暂停买入」（c0b051e）。
- **口径铁律**：前窗口低点用 `low.shift(5).rolling(20).min()`（滚动窗口会吞掉创新低）；经济对比用 Σ(放行日 pnl) 对基准 + 配对差表（拦截正 pnl 记 0 会虚抬模型）。

全量数据、已毙候选明细与落地待办见 [references/stability-patrol-validation-2026-10-28.md](references/stability-patrol-validation-2026-10-28.md)；理论轮方法论、滚动窗口泄漏 bug（`low.shift(5).rolling(20).min()`）、震荡窗口代价（29.4% 基准 + 两面交付）与经济口径公平性见 [references/stability-theory-and-econ-fairness-2026-10-28.md](references/stability-theory-and-econ-fairness-2026-10-28.md)。

## 趋势持有 + 回撤加仓波段（2026-10-28）

用户提出「长期持有底仓 + 跌狠了买、涨回来卖」的持有型策略时，它与网格是两个物种：
网格赚日常波动（高频小额），回撤加仓赚危机回撤（低频大额）。当用户拿「涨了十年」当
买入理由时必须给两面（长牛事实 + 最大回撤史 + 当前位置 + QDII 溢价纪律），不许顺叙事走。
参数化回测 → D=8%/R=10% 在 513100 两年半 9买9卖全部 +10~12% 离场、波段收益为纯持有的
134%，但最深套牢 −15.8% 必须交底。选品沿用同指数「溢价最低+成交最大」。数据源坑：
东财日K上限 300 根，长回测走腾讯 fqkline（close 在第 3 位）。
完整案例与回测明细见
[references/trend-holding-drawdown-averaging-2026-10-28.md](references/trend-holding-drawdown-averaging-2026-10-28.md)。

## 巡检/榜单的呈现纪律（2026-10-28）

- **放行率是市况函数，不是常数**：122 日均值 75%，最近 20 日可以只有 25%——用户拿两数对照问过。任何长期均值必须配「近20日实测」一起给；拦截成段集中（实测 4/6/14 连续天），平时零拦截，汇报给连续段表而非单一百分比。
- **榜单「近20日往返」与门控放行率同涨同跌**（同段行情两支温度计）。窗口滑出肥肉段会让榜首掉到 58 名——这是窗口滑动，不是行情突变。
- **行情形态标签必须带方向**（用户：「写个单边干什么」）：单边上涨/单边下跌/阴跌/震荡四档，判据 ER≥0.45±net 正负 / ER<0.35且net≤−5% / 其余。阴跌是最隐蔽的网格陷阱：它过「近20日往返≥2」入榜门槛但每次接回锚点都在下移——榜单加形态列就是为了暴露它。标签低 ER≠震荡（末段阴跌 ER 可 0.16）。
- **当天可操作性模拟**：每日 D 用截至 D−1 收盘判定（无前视），再用分钟级 bars 验证买/卖点触发（prev_close/1.015 与 ×1.015）；被拦日里触买点的次数=真实避损，必须追踪这些被避掉接货的后续盈亏（如 09-24@0.932 → −14.4% 至今未解）。单持仓状态机会低估多格实盘，需声明。

## Instrument data endpoints under rate-limiting (2026-10-27)

同类粗筛/深评取数（费率/规模/成立日/净值/成交额）在 akshare+push2 被限流时的降级链：fundf10.eastmoney.com 概况页、FundArchivesDatas gmbd 规模接口、pingzhongdata 净值序列、腾讯 qt/fqkline。跟踪误差必须用净值口径；增强型 ETF 的偏离是主动增强不是跟踪失败；指数基准缺位时标数据缺失，禁用近亲指数硬替。见 [references/instrument-data-endpoints.md](references/instrument-data-endpoints.md)。

## Verification checklist

- User constraints, assumptions, and unresolved questions clearly separated.
- Tickers, fees, index data and dates verified from documents, not search snippets alone.
- Allocation and scenario arithmetic actually computed.
- No static stress test mislabeled as a path-dependent grid backtest.
- No annual volatility mislabeled maximum drawdown; no dividend yield mislabeled payout.
- Bear case, failure triggers, and a risk-budget breach scenario included.
- Live-data or simulation gaps explicitly disclosed.
- Final conclusion does not overstate what was verified.
