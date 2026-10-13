# Methodology — ETF Grid Screener

This document explains how `scripts/grid_tool.py` selects grid-trading candidates and
computes grid parameters. Read it when tuning thresholds, debugging empty results, or
replacing a data source.

## 1. Eligible universe

The built-in `UNIVERSE` lists T+0 ETFs / LOFs only (gold, commodity futures, cross-border
QDII, cross-border LOF). Money-market ETFs are excluded by design (near-zero volatility
makes grid trading pointless). Override with `--universe <csv>` (columns: `code,name,kind`).

### 1.1 Auto-merged all-market ETF pool + snapshot freshness (`v1.0.32`)

Unless `--no_a_share` / `--universe` is given, the tool merges in the whole market of
equity ETFs (**~1284 names**): A-share ETFs gated at 5-day-avg **and** previous-day
turnover ≥ `--min_amount_a` (default 100M), plus cross-border ETFs gated at ≥ 50M.

The name list comes from `a_share_etf_pool.json`, a snapshot shipped **inside the
package** next to `grid_tool.py` (path resolved via `__file__`). This guarantees a
full-market scan straight out of the box.

**Two online sources, tried in order (`v1.0.33`)** — the list is no longer a dead end:

1. **Primary** — `push2.eastmoney.com/api/qt/clist/get` (`fs=b:MK0021`, the ETF board).
   This is what produced the historical list, but in some networks the whole
   `push2.eastmoney.com` host is connection-reset (verified: `clist/get`, `stock/get` and
   the `82.push2` mirror all fail, while `api.fund.eastmoney.com` is fine). Page 1 is
   therefore fetched with **only 2 retries as a liveness probe** — if it fails the source
   is abandoned immediately instead of grinding through the full retry budget (~76 s).
2. **Fallback** — `fund.eastmoney.com/js/fundcode_search.js`, a ~3 MB static file listing
   **all 27k+ funds** with a type field (same domain as the NAV endpoint, measured
   reachable, **~0.4 s**). Filtered by `type == "指数型-股票"`, an exchange-traded ETF
   **code-prefix allowlist** (`159/510/511/512/515/516/517/518/530/560/561/562/563/588/589`)
   and the script's own `_classify_aetf` (keeps `股票A` / `跨境`).

   The prefix allowlist was derived empirically by reverse-engineering the existing list:
   it reproduces **99.3%** of it and additionally picks up ETFs listed since (e.g.
   `159010 港股通科技ETF博时`), while naturally excluding OTC funds (`000/001/…/519`),
   LOFs (`16x/501/502`) and QDII (`513/520`).

Whichever source succeeds is written back as the new snapshot. Measured end-to-end on a
network where the primary is blocked: **2.2 s** instead of 76 s of failure.

Because a snapshot ages, the tool never uses one silently:

- It reads the snapshot's mtime. If older than `--pool_max_age` (default **30 days**),
  it attempts an online refresh first.
- Refresh succeeds → new snapshot written, no warning.
- Refresh fails → the run **continues on the old snapshot** (still far better than the
  96-name fallback) but prints the snapshot date, its age, and an explicit warning that
  ETFs listed after that date are missing. The report footer carries the same date.
- No snapshot at all **and** online fetch fails → prints a clear warning that only the
  built-in 96-name T+0 pool is being scanned, so A-share ETFs are absent.

`--refresh_a_pool` forces an online refresh regardless of age. If you redistribute this
skill, refresh the bundled snapshot periodically so users start from a current list.

## 2. Selection criteria (four conditions)

A candidate must pass the hard filters below. The box-validity filter (§3) and the
no-downtrend filter (§4) are non-relaxable. The loose criteria (§1, §2) are widened by
the fallback stages in §6.

1. **MA convergence (黏合)** — dispersion of MA5/10/20/60 stays within `--conv`%.
   Lower dispersion = flatter, more "grid-friendly" price action.
2. **Horizontal oscillation (横盘)** — near-1-month amplitude ≤ `--amp20`% and near-2-month
   amplitude ≤ `--amp40`%; annualized volatility ≤ `--vol`%.
3. **Box validity (箱体有效性)** — a hard, non-relaxable filter (see §3). Requires at
   least two swing highs forming an upper rail and two swing lows forming a lower rail,
   with alternation in time, a minimum oscillation span, and the current price still
   inside the box.
4. **No downtrend / no new lows** — 40-day linear-regression drift below `-trend_max`%, or
   a recent 40-day new low, is excluded.

Liquidity: LOFs (and all instruments when `--liquid_all` is set) must have a 5-day
estimated average turnover ≥ `--min_amount`. Turnover is estimated as
`volume(lots) × 100 × VWAP` because the endpoint returns volume in lots (1 lot = 100
shares); magnitudes and ranking are reliable, labelled "估算").

### 2.1 High-premium hard filter (高溢价硬过滤) — `v1.0.30`

Cross-border (QDII) and LOF ETFs can trade at a large premium over NAV. A grid sets its
buy/sell bounds by the **traded price**, so if you buy at a high premium and the premium
later collapses, you take an extra loss on top of normal grid swings. To avoid this trap:

- Before selection, the tool pre-fetches NAV for **every** de-duplicated candidate
  (all ~126–266 names, not just the final picks) and computes
  `premium% = traded_price / NAV − 1`.
- Any instrument with `premium% > --max_premium` (default **10.0%**) is dropped by the
  hard filter in `passes()`, regardless of how good its box looks.
- A candidate whose NAV cannot be fetched (`premium = None`) is **kept conservatively** —
  we never kill a name just because the NAV endpoint hiccupped.
- Disable entirely with `--no_premium_filter` (or set `--max_premium 999`); A-share ETFs
  that already trade near NAV are unaffected.
- The chosen report still prints each pick's premium (red ⚠ badge when `> 3%`) so the
  user can sanity-check before trading.

The filter is a pure safety net: it only removes clearly over-priced cross-border/LOF
names; it never widens or shifts any grid bound.

## 3. Box identification (箱体识别) — the hard filter

A grid only earns money while price oscillates between two rails. Anything else — a
one-way trend, or a brief pause after a run-up — is not a box and must not be screened
in, no matter how good the other indicators look. This filter runs inside `evaluate()`
and is **never relaxed** by the fallback stages, so a genuinely box-less instrument can
never be rescued by `--min_results`.

The algorithm (`identify_box`):

1. **Swing extremes** — over the last `--box_window` days, mark swing highs / swing lows
   (a bar whose high/low is the extreme within ±`BOX_SPAN` bars).
2. **Rail clustering (price-string)** — 
   *Upper rail*: sort swing highs by price and connect adjacent highs whose prices differ
   by ≤ `--box_tol`% into a "string". A string with ≥2 members becomes a candidate rail;
   the bound is the **highest price in the string** (the highest high inside the box,
   giving the sell line more headroom and reducing early sell-outs).
   *Lower rail*: anchor on the **lowest swing low within the last `--lower_rail_stale`
   days** (excluding today), then collect all swing lows within `--box_tol`% of that
   anchor into a cluster. The bound is the **lowest price in that cluster**. This makes
   the lower rail track the *real recent support* instead of being pushed up to the
   highest low in a wide string. The tolerance starts at `--box_tol` and widens in 0.25
   steps, but is **capped at `min(3.0%, window amplitude × 0.35)`**.
3. **Time alternation** — sort the rail-touch points by date and count high↔low switches.
   Requires ≥ `--box_min_alternations` (default 3) alternations. `低 高 低 高` = a real
   box; `低 低 高 高` = a trend that paused, which is rejected.
4. **Minimum span** — the box must have oscillated for at least `--box_min_days` trading
   days (first rail touch → last rail touch). A 9-day consolidation after a rally is not
   a box.
5. **Still active (recency rule)** — the most recent member of either rail cluster must
   be within `--box_max_stale_days` (default 50) of the end of the window. If the price
   left the box area more than 50 days ago, the old highs/lows are no longer a current
   box and the candidate is rejected.
6. **Price still inside** — current price above `upper × 1.002` (broken out upwards) or
   below `lower × 0.998` (broken down) is rejected.
7. **Minimum grid count** — the box must be wide enough to yield ≥`--box_min_grids` grids
   at the instrument's own ADR spacing. A box that only fits 2 grids has no grid value.

The upper/lower bounds reported to the user are the **actual rail-touch prices** from the
clusters, not percentile estimates of the `--box_window` range (default 80 trading days).

## 3.5 Golden-ratio bounds (optional `--bounds golden`)

As an alternative to the rail-cluster box, the script can derive bounds from a Fibonacci
retracement of the recent high/low range, similar to the Tongdaxin 主力黄金线 formula:

- `top` = highest high over the last `--gold_window` days, excluding the most recent
  `--gold_lag` days (`REF(HHV(HIGH,window),lag)`).
- `bottom` = lowest low over the same window (`REF(LLV(LOW,window),lag)`).
- Reference lines are drawn at 0.0, 0.236, 0.382, 0.5, 0.618, 0.809, 1.0 of the range.
- The default grid band uses **0.618 as the upper bound and 0.382 as the lower bound**
  (`--gold_upper 0.618 --gold_lower 0.382`, the 六一八/三八二 band). Users can override to
  the wider 0.809/0.236 band, the full range (`1.0 / 0.0`), or any other pair.

### 3.5.1 Support/resistance correction (压力/支撑位修正)

A single HHV/LLV over the window can land the Fibonacci lines at arbitrary spots — an
isolated spike in the window moves the whole band, so the lines may not sit on the levels
a human actually sees. When a box/range has run a long time, the meaningful bounds are the
**repeatedly-touched support/resistance levels from further back in history**. The tool
corrects the Fibonacci band toward those levels, widening only (never narrowing):

1. **Histogram peak detection** (`_hist_peaks`) — over the last `--gold_pressure_window`
   (default 250) days, bucket all daily highs (for resistance) and all daily lows (for
   support) into a price histogram (bin = `--gold_bin_frac`, default 0.4% of price). A
   price that was touched many times forms a local maximum ("peak"); the peak's average
   price is that "level". A level needs ≥ `--gold_min_touches` (default 3) touches to count.
2. **Raise the upper bound (sell line)** — only when the current price is within
   `--gold_correct_near`% (default 4%) *below* the golden upper (i.e. the sell line is
   being actively challenged). Then snap it up to the nearest resistance peak whose gap
   above the golden upper is within [`--gold_pressure_min_gap`, `--gold_pressure_tol`]
   (default [1%, 5%]). Rationale: keep the sell line conservative — raise it only when
   price is knocking on it, and only to a real, repeatedly-touched high.
3. **Lower the lower bound (buy floor)** — snap it down to the nearest support peak whose
   gap below the golden lower is within [`--gold_correct_near`, `--gold_pressure_tol`]
   (default [4%, 5%]). The 4% floor skips the *current* consolidation zone (a support only
   1–3% below is just the recent chop, not a real floor) and reaches the deeper historical
   support that price has repeatedly bounced off.

This mode still requires the current price to lie inside the corrected band and still
applies the trend/oscillation filters; it replaces the rail-cluster hard filter with a
Fibonacci-based band that is then snapped to real support/resistance. The sparkline shows
the full set of golden-ratio reference lines as faint orange dashes.

**Box mode uses the same correction.** In `box` mode the starting point is the rail-cluster
top/bottom from §3 (not a Fibonacci band), but the identical histogram-peak widening is
applied: the upper rail is raised to the nearest repeatedly-touched **resistance** (gap within
[`--box_pressure_min_gap`, `--box_pressure_tol`] above the cluster top) and the lower rail is
lowered to the nearest repeatedly-touched **support** (same gap band below the cluster
bottom). The correction is **only-expand** — the band never narrows. If no such level exists
within the tolerance, the upper bound falls back to cluster-top + `--upper_buffer`% (the
original box behaviour) and the lower bound stays at the cluster bottom. Parameters:
`--box_pressure_window` (default 250d), `--box_pressure_tol` (5%), `--box_pressure_min_gap`
(1%), `--box_bin_frac` (0.4%), `--box_min_touches` (3). Because a well-formed box already
captures its extreme touch levels in the cluster, this correction usually does not fire for
clean boxes; it engages mainly for boxes that have a secondary touch level just beyond the
main cluster (e.g. a slightly higher resistance the price tested once or twice).

**Why all daily highs/lows, not just swing points:** "price touched a level" does not
require a strict local extreme — a candle whose high merely reaches the level still counts
as a touch. Using the full high/low series as histogram material is what makes the
repeated-touch levels (e.g. a 3.12 resistance touched 30+ times over 9 months) show up
cleanly as histogram peaks.

**Touched vs nearby (reporting distinction):** the per-card "箱体确认" line and the CSV
split rail contact into two numbers. In the UI these are labelled with plain words
(`碰线次数` / `附近高点` / `附近低点`), never with jargon like "cluster":

- `碰线次数` = swing highs whose `high ≥ upper × 0.999` (or swing lows whose
  `low ≤ lower × 1.001`) — candles that actually touched the upper/lower dashed line in
  the sparkline. This is what a human can see at a glance.
- `附近高点` / `附近低点` = total swing highs/lows inside the tolerance band
  (`判定宽度`, the plain-language label for what the code calls tolerance) used to define
  the rail. These include near-but-not-on touches; they are why the algorithm believes
  the rail exists, but they do **not** correspond to visible contacts.

A wide gap between the two (e.g. 碰线 1 次 / 附近高点 6 个) means the rail was truly tested
once but is mostly made of near-but-not-on candles — the rail is "soft". Use the touched
count to judge rail strength at a glance.

**Terminology rule for user-facing text:** the report is read by non-technical retail
investors. Avoid jargon — write 判定宽度 not 容差, 附近高点 not 聚簇、碰线 not 触线.
Jargon is acceptable only in code identifiers and comments.

### 3.5.2 Golden-mode box confirmation (MA20 crossing filter)

A Fibonacci band alone can still land on a one-way trend — a falling knife has a clear
"high" and "low" too, but it is not a box. Golden mode therefore adds a second, hard,
non-relaxable check: over the last `--gold_window` trading days, the closing price must
cross its own 20-day moving average **at least `--gold_min_ma20_cross` times** (default 3).
Each crossing = one up/down swing around the average; a real box oscillates and racks up
many crossings, while a single-direction trend has few or none. Candidates below the
threshold are excluded with the reason "无箱体震荡(单边趋势)". This is what stops a
visibly-trending ETF from being screened in just because it has a high/low range.

## 3.6 Same-index de-duplication (同指数去重)

Two or more ETFs often track the same index (e.g. 华安/易方达 上证50ETF), and their grids
are interchangeable. After the hard filters, the tool groups candidates by the index/theme
inferred from the fund name (a keyword table, longest match wins; unrecognised names stay
independent and are never wrongly merged) and keeps **only the highest-scoring ETF per
index**. This collapses the duplicate-cluster problem (the user saw 33 results with many
tracking the same index) down to one representative per index. Disable with `--no_dedup`.

### 3.6.1 Liquidity-first representative (`v1.0.31`)

De-duplication runs **before** the liquidity hard filter. If the group's top-scoring ETF
happens to fail its own liquidity gate, the whole index would be wiped out later — while
the genuinely liquid, mainstream ETF in the same group had already been discarded as a
"runner-up". Real case: the 上证50 group's top scorer was 上证50ETF建信/天弘 (5-day average
turnover below the 1亿 A-share gate), so 上证50 vanished from the report entirely even
though 510050/510100 trade heavily.

Fix: within a group, sort by `(liquidity_gate_ok, score)` descending, so a **liquid**
representative is preferred; the score only breaks ties among equally-liquid candidates.
The gate uses the strict (non-relaxed) threshold for each kind — `A股ETF`: 5-day average
≥ `--min_amount_a` **and** previous day ≥ `--min_amount_ystd`; `LOF`: ≥ `--min_amount`;
`跨境A`: ≥ 50M. If no member passes the gate, the group falls back to top score (no
regression, the group is simply filtered out later as before).

## 4. Composite score (0–100)

Higher = more suitable for grid trading. Weights:

| Component | Weight | Input |
|-----------|--------|-------|
| MA convergence | 25% | `sc_conv = 1 - conv / --conv` |
| Volatility | 20% | `sc_vol = 1 - ann_vol / --vol` |
| 1-month amplitude | 15% | `sc_amp = 1 - amp20 / --amp20` |
| Price position | 20% | `sc_pos = 1 - 2*|rel - 0.5|` (rel = current price position in channel) |
| Trend flatness | 20% | `sc_trend = 1 - |drift| / --trend_max` |

`score = 100 × (0.25·sc_conv + 0.20·sc_vol + 0.15·sc_amp + 0.20·sc_pos + 0.20·sc_trend)`

Results are sorted by `score` descending; the top three are flagged "★ 推荐".

## 5. Grid parameters

- **Upper / lower bound** — in `box` mode, the rail-touch prices identified in §3 (not
  percentiles). In `golden` mode, the chosen Fibonacci retracement levels from §3.5, then
  corrected toward repeatedly-touched support/resistance levels (widening only, §3.5.1).
  `--ub_pct` / `--lb_pct` are retained only for backwards compatibility and are unused.
- **Upper-bound buffer (--upper_buffer, default 1.5%)** — in `box` mode, the displayed upper
  bound (the grid sell line) is lifted by `--upper_buffer`% above the real upper rail, to
  reduce premature selling ("卖飞") during upswings. This buffer is the **fallback** when the
  support/resistance correction (§3.5.1) finds no real resistance within tolerance — if a
  repeatedly-touched resistance does exist just above the cluster top, the sell line snaps to
  that resistance instead (no extra buffer is stacked on top). The breakout filter and the
  touch-count still use the real upper rail, so a genuinely broken-out instrument is never
  wrongly kept; the base price stays at the true box midpoint (it does not drift up with the
  buffer). In `golden` mode no buffer is added; the upper bound is the Fibonacci level plus
  the support/resistance correction.
- **Base price (中枢)** — midpoint of true upper/lower rail; the most balanced price to start from.
- **Grid spacing** — by default the instrument's own Average Daily Range (ADR, near-1-month
  true range), floored at 1% (avoids grids so tight that fees eat returns). Override with
  `--step` (fixed %) or `--grids` (fixed count).
- **Grid count** — channel width ÷ spacing.

## 6. Fallback relaxation (数量兜底)

If strict filtering yields fewer than `--min_results` instruments, the tool escalates
through four relaxation stages (`STAGES`), widening `conv / amp20 / amp40 / vol / trend`
and lowering the liquidity floor, until it reaches `--min_results`. Relaxed candidates
score lower and are kept with a note. Disable with `--no_fill` to output strict-only.

Note: relaxation only widens the *loose* criteria. Box validity (§3) is enforced in
`evaluate()` and can never be relaxed — if nothing forms a real box, the honest answer is
a short list, not a padded one.

## 7. Data sources (unofficial, may change)

| Data | Endpoint | Notes |
|------|----------|-------|
| Daily K-line (qfq) | `proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get` (Tencent) | No key. Unofficial web API; if it changes, replace `fetch_kline()`. |
| Fund NAV / premium | `api.fund.eastmoney.com/f10/lsjz` (Eastmoney) | No key. For cross-border ETFs NAV may lag 1–2 days; premium is an estimate. |

**Replacing a source:** both fetchers are isolated functions (`fetch_kline`, `fetch_nav`).
Swap the URL/parsing without touching the scoring or grid logic. If both endpoints break,
the script still runs but returns "无行情数据" for affected codes.

## 8. Limitations

- Universe is hardcoded and must be updated as new T+0 ETFs/LOFs list.
- Premium/NAV is estimated; do not treat as exact.
- Box identification is stricter than a simple range check, so the result list is shorter
  by design. This is intentional: a grid on a non-oscillating instrument loses money.
  Use `--box_min_days` / `--box_min_grids` to trade strictness against list length.
- The tool performs **no back-test**. Historical box behaviour does not guarantee the box
  will hold; a breakout invalidates the grid.
- Outputs are historical-data calculations, not forecasts. Always pair with the embedded
  risk disclaimer.
