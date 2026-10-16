# Ledger-derived morning grid advice

## Why separate paths
A fixed grid price is calculated from confirmed fills, not the vendor's latest print. Requiring a same-day 09:30+ quote unnecessarily delays advice and makes a network outage block an otherwise deterministic calculation. This does not make auction prices executable or prove a broker fill.

## Verified integration
- Existing cron: `e01b833b150d`, changed in place to weekdays 09:24 Beijing, same Feishu destination.
- Installed entry: `scripts/grid_weixin_execute.py`; source launcher under `tools/confirmed_grid/launchers/`.
- Launcher calls `ops_main --phase grid`; grid branch renders `plan(root_from_home())` before `fetch_quotes()` and labels it ledger-derived, not live-market pricing.
- Other phases retain quote validation; intraday monitoring is not made premarket by this change.

## Regression and rollout
1. Add a test with premarket phase and a fetch_quotes stub that raises if called. Assert grid actions and the ledger/no-live-quote label appear.
2. Watch the test fail before implementing the branch.
3. Run runtime/holdings integration tests and the installed launcher locally. Local output verifies generation, not remote delivery.
4. Update existing cron, then list/read back schedule, destination, script, enabled state and next_run_at.
5. Commit/push only task code/tests; do not include unrelated dirty research files or generated ledger data.

Session validation: 18 relevant tests passed and installed launcher generated the advice; commit `1a718bd`. At completion the next scheduled run was 2026-10-19 09:24, not a retrospective send for the elapsed 2026-10-16 slot.
