# Period summary format (user requirement, 2026-10-16)

The user asked for a 「二、合计」 that folds in trading days and capital, anchored from 2026-09-23.

## Required fields

| Field | Source |
|---|---|
| 交易天数 | Trading days in the stated period, computed from the start date the user gives — not from how many distinct `date` values happen to be recorded |
| 买入金额合计 | Sum of `amount` for `side == buy`, per ETF and total |
| 卖出金额合计 | Sum of `amount` for `side == sell`, per ETF and total |
| 佣金合计 | Count of legs × 1.00 (万一, 1 CNY minimum); locally estimated, not broker-confirmed |
| 净投入 | buy_amount − sell_amount + commissions; per ETF and total |
| 持有份额 | `qty` from the sub-ledger |
| 做T累计净利 | `t_net`, with round count |

## Rules

1. **Confirm the start date with the user.** The user anchors periods at a fixed date (currently 2026-09-23). Do not derive it from the earliest recorded trade.
2. **Never backfill `date: null`.** Earlier trades with null dates stay null. Do not invent dates or substitute old ticket data.
3. **State the口径 explicitly:**
   - 净投入 is cumulative net cash outflow, not current 占用 / margin usage.
   - Commissions are locally estimated (万一, 1 CNY minimum per leg), not broker-confirmed.
   - Account cash, frozen shares, and pending orders remain unreconciled.
4. **Per-ETF breakdown before the total.** The user cross-checks line by line.

## Trading-day count must exclude A-share holidays (user correction, 2026-10-16)

**Do not count weekdays only.** The first version of this summary reported 18 trading days for 2026-09-23 → 2026-10-16, and the user immediately caught it: 「认真算一下，是18个交易日吗？大A放假你算了没」.

Weekday counting is wrong twice over:
1. It ignores weekends — but that is the easy half.
2. **It ignores A-share market holidays.** A "trading day" is a day the exchange is open, not a day that is Monday–Friday.

2026 official holidays in this window (国务院办公厅关于2026年部分节假日安排的通知, verified against SSE 休市安排):
- **中秋节**: 2026-09-25 (Fri) → 2026-09-27 (Sun) — 休市 3 days
- **国庆节**: 2026-10-01 (Thu) → 2026-10-07 (Wed) — 休市 7 days
- 2026-10-10 (Sat) — 周末休市 (调休上班日, but the exchange is closed)

Correct count for 2026-09-23 → 2026-10-16: **24 calendar days, 11 trading days**:
09-23, 09-24, 09-28, 09-29, 09-30, 10-09, 10-12, 10-13, 10-14, 10-15, 10-16.

**Rule:** compute trading days from the stated start date against an explicit holiday set (verify the year's official notice — it changes every year), not from `len([d for d in range if d.weekday() < 5])`. State the holiday set you excluded. A number with no holiday list behind it is not a trading-day count.

Also: the trading-day count is the **calendar** count for the period. It is NOT a claim that a trade occurred on each of those days. Most historical trades in this ledger have `date: null`; only a few dates are recorded. Say both things.

## Verified 2026-10-16 numbers (reference only, superseded by 2026-10-20 below)

Period 2026-09-23 → 2026-10-16: 24 calendar days, **11** trading days (corrected from the earlier wrong 18).

| ETF | Trades | Buy amt | Sell amt | Commissions | Net invested | Qty | T rounds | T net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sh589720 | 18 | 95,688.10 | 48,446.00 | 18.00 | 47,260.10 | 57,700 | 6 | 747.60 |
| sz159363 | 19 | 82,051.40 | 30,202.50 | 19.00 | 51,867.90 | 45,600 | 5 | 535.00 |
| sz159992 | 6 | 31,770.50 | 16,224.40 | 6.00 | 15,552.10 | 18,300 | 2 | 315.60 |
| **Total** | **43** | **209,509.90** | **94,872.90** | **43.00** | **114,680.10** | **121,600** | **13** | **1,598.20** |

Only 2026-10-14, 10-15, 10-16 have non-null trade dates in the ledger; 159992 has zero. The 18 trading days is the calendar count, not a claim that trading occurred every day.

