# ETF grid migration and reminder gates

## Verified recipe from the September 2026 migration work

- Migration policy: source `sz159992`, target `sh589720`, stage `awaiting_broker_reconciliation`.
- Source is exit-only. Remove source buys/rebuys from current suggestions, but retain legacy orders in a reconciliation list.
- Target buys remain disabled until the broker confirms old source orders, actual fills/cancellations, available cash/frozen orders, and a fresh target quote including timestamp and premium/discount.
- `159363` remains unchanged.
- Shared innovation-drug cap remains RMB 46,000; total account remains RMB 100,000; cash floor remains RMB 20,000; grid gap remains 2%; third ETF remains research-only.

## Reminder gates

1. At the very start of the script, check session day/holiday. Return quietly for non-result invocations on holidays before loading the ledger or fetching quotes.
2. For 09:31 execution, require every quote timestamp to be the same day and at or after 09:30. Otherwise render a preview marked `勿下单`.
3. Render source reconciliation language and a source exit suggestion only when T+1 inventory and existing order reservations allow it.
4. Intraday high/low alerts should use one deduplication map keyed by trading day, code, side, and level. State that the extreme may predate the recommendation and ask the user to check the broker.
5. Close review is advisory only and must not rebase the retiring source ETF or change the gap.

## Regression fixtures

The reliable regression shape is represented by `test_grid_notifications.py`: patch clock, CLI args, ledger/quote functions, use temporary fixture paths, capture stdout, and assert both positive safety language and absence of target/source-buy rows. Run `python -m unittest discover -s . -p 'test_grid_*.py'` from the scripts directory. In the verified run this produced 44 tests and `OK`; also compare SHA-256 values for the real ledger, active ticket, and intraday state before and after.
