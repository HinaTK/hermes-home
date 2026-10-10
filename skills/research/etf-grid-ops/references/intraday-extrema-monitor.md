# Intraday grid touch monitoring: original day-extrema mode

## User-selected tradeoff (2026-09-30)
The user explicitly rejected the minute-K-line / last-30-minutes experiment and requested the original monitor, accepting historical-extrema false reminders. This supersedes the first-observation baseline and ticket-time-gated minute implementations. Do not silently re-enable either scheme.

Current `grid_weixin_intraday.py` behavior:
- Fixed 10-minute cron, trading-session gate 09:35–14:57 (first normal check 09:40); require a same-day 09:30+ Tencent quote. 09:10 local preview, 09:31 Feishu action advice and 15:20 EOD review remain unchanged.
- Compare cumulative same-day low with pending buy prices, high with pending sell prices; current spot is additional touch evidence. Extrema and spot use ONE `trend_alert` entrypoint and ONE per-code/side/price/day `alerts` map. After a high/low reminder, a later current-spot crossing of that same pending level must not send another confirmation message. Removed the old independent `fill_alert`/whole-ticket `fill_alerted` notification path. Missing extrema use current spot even at first observation and label the evidence `现价`, not an invented day high/low. Other unreminded levels remain independent.
- No minute-feed call, no rolling 30-minute filter, no issuance / first-observation cutoff. Ticket generation no longer adds minute-monitor issuance metadata; existing ticket fields are harmless and ignored, not rewritten.
- Label evidence “今日最高/最低” and warn “可能发生在建议挂单之前，挂单不等于成交，请核对银河委托/成交”. Example: low 0.839 may generate a verification reminder for a later 0.846 suggestion even with current price 0.862. This is the accepted false-reminder tradeoff, not evidence of a fresh post-order touch.
- Dedup once per code/side/price/trading day; preserve current alerts on rollback and action changes, reset on the next session. Do not clear live state just to resend already-reminded prices. Same-day repeated touches of a replacement order at the same price are not guaranteed a second alert.
- Never auto-book a touch, place an order or cancel a broker order. A quote high/low cannot prove actual order placement time, fills or available shares; use 银河 records and explicit fill reports.

Verification: tests use temporary tickets/state and compare real-ledger/ticket checksums. Exercise the pending-ticket main flow with a minute-feed trap to prove no minute request is made. Cron enabled/ok is not proof of Feishu delivery. Quote failures, stale/extreme data and one-shot dedup still prevent a zero-miss guarantee.

Historical incident: 2026-09-30 opening low 0.839 was compared with a later 159992 buy suggestion 0.846. Initially changed to conservative filters, then rolled back at the user's request; only the disclosure remains, without those filters.
