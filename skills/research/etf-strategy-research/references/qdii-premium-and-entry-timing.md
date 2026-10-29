# QDII premium analysis and entry-timing regime toolkit (2026-10-24, 159866 case)

Case: user asked whether 159866 (日经ETF工银) was a buy; the assistant initially anchored on the user's own three-tranche plan, then was told "不要管我的方案，重新用 etf-analysis skill 来判断" — re-analyzed from scratch. Lessons and numbers below.

## Premium freshness: the −0.05% → +2.35% trap

On 2026-10-22 the assistant reported premium −0.05% using the **10-21 NAV** while price was 10-22's; Tokyo had fallen ~2.4% on 10-22, and when the fresh NAV (1.5731) landed the real premium was **+2.35%**. A premium-based early-buy trigger was invalidated by the data refresh. Rule: always print NAV date next to premium; re-derive premium from the freshest NAV immediately before any premium-gated action. Cross-border NAV lags the A-share close — same-day NAV arrives in the evening.

## Premium percentile over ≥100 aligned NAV days (Eastmoney F10 lsjz API)

Endpoint: `https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex={page}&pageSize=50&_=1` with Referer `http://fundf10.eastmoney.com/` and a UA. `pageSize=250` returns a list-index error — page through 50s. Align NAV dates to Sina daily closes with up to 3 days backfill for unmatched dates.

159866 (100 aligned days): mean +2.89%, median +2.36%, min −0.02%, max +7.74%; **79% of days above +2%, 12% above +5%, discount days ~1%**. Current +2.35% = exactly the 50th percentile → structural premium, quota-constrained.

Same-index vehicle comparison (all four Nikkei-225 ETFs, same day):

| code | premium | 20d avg turnover |
|---|---|---|
| 159866 工银 | +2.35% (lowest) | 3.07亿 (largest) |
| 513520 易方达 | +3.77% | 2.59亿 |
| 513000 景顺 | +3.60% | 1.70亿 |
| 513880 华安 | +4.99% | 2.05亿 |

Selection rule: same-index lowest premium + highest liquidity wins → 159866. Premium's ONLY other use: >5% = do-not-buy extreme alert. "Wait for premium ≤ 0" on a structural-premium product is an infinite wait.

## Four-signal bull/bear regime check (script pattern)

1. **MA50 vs MA200** (golden/dead cross) + price vs MA200 — bull framework intact? Historical golden/dead-cross events with +60-session forward returns show why this is the anchor signal.
2. **Pivot structure** — 20-day rolling swing highs/lows: higher-highs+higher-lows = uptrend; both lower = downtrend; divergent (159866: highs 1.920→1.764 lower, lows 1.523→1.621 higher) = **converging triangle**, direction pending. A split structure IS the answer — present the split, don't force a verdict.
3. **Drawdown band** from 250-day high: 0~−10% high zone / −10~−20% correction / −20~−35% bear / deeper = deep bear. −20% is the classic bull/bear dividing line.
4. **Realized vol vs own median** (20d, annualized): spike (>1.2×) = bear-start panic signature; normal = correction more likely than regime change.

159866 readout: framework bull (MA50>MA200 +7.2%, price +2.2% above MA200), structure split, drawdown −16.1% (correction zone), vol 27% vs median 26% (no panic) → "bull-framework mid-term correction". Concrete invalidation: sustained break of MA200 ≈ 1.575 (only −2.2% away) → cut early, before any −25% stop.

## Left vs right entry event study (script pattern)

On the fund's own daily history (500 bars): left signal = close < MA20×0.97 while falling; right signal = MA20 reclaim day. Report 20- and 60-session forward returns (mean/median/worst/best), win rate, and path max-drawdown. 159866 result: left mean +16.6% / win 93% / worst −2.4% vs right +6.2% / 67% / worst −14.2% — left dominated, BUT disclose the regime bias: the whole sample sat in a bull framework, so left-side stats are inflated by beta; left's uncovered tail is a trend that never returns (that's what the MA200 invalidation line is for).

## Reproduction

Scripts from the session: `D:/Code/AH_analyse/tools/etf_analysis_159866.py` (same-index comparison + scoring) and `tools/etf_analysis_159866_v2.py` (premium percentile via paged NAV API + regime signals). Kline via `grid_tool.fetch_kline` (screener skill scripts); NAV via `grid_tool.fetch_nav` returns `(nav, nav_date)` tuple.
