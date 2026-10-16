# Cost reconciliation: accounting and authorization boundaries

The reviewed conversation contains incorrect calculations and unsupported claims of completed repairs. Do not reuse its old holdings, cash, quotes, fee splits, or script-success assertions as audited facts.

## Required distinctions

- Buy cash outflow = execution quantity × actual execution price + buy fee.
- Sell cash inflow = execution quantity × actual execution price − sell fee. A buy price or average carrying cost must never replace the actual sale price here.
- Inventory carrying cost is reduced according to an explicitly declared method (FIFO, moving average, etc.). A grid trigger label is not necessarily the T+1 lot consumed.
- Cumulative net investment = total buy outflows − total sell inflows. Divide by remaining quantity for a net-investment unit cost; this intentionally incorporates prior sale gains/losses and must not be mislabeled as remaining-lot acquisition cost.
- Per-ETF isolated cash illustrations are not whole-account cash when other instruments traded.

## Review before repair

1. Locate current authoritative ledgers/runtime; do not assume the old ledger.json is still active. Preserve originals and use read-only calculations first.
2. Obtain broker statements for a disputed reconstruction; local tickets/history are provisional, not confirmation of each fill.
3. Resolve exact fee language. The conversation includes both 最低1元 and 最高1元; they are not interchangeable. Do not infer the user's intended rule from earlier assistant statements.
4. Calculate in Decimal from raw fills; show execution amount, fee, cash delta, remaining quantity, cumulative net investment and its unit cost. Report carrying-cost methodology separately if needed.
5. Reconcile beginning cash plus all actual cash movements to ending cash, quantity sums to position totals, and carrying-cost/realized/unrealized totals under the same methodology. Identify unresolved differences without declaring them immaterial.
6. Only apply explicitly scoped, evidence-backed corrections. Never replay a one-off historical booking script just because the user challenged a report. Retain zero-quantity historical records unless a deliberate data-retention policy says otherwise; their existence alone is not an accounting defect.
7. Report what was actually calculated, what changed, and what remains unverified. Successful file writes or process exit codes do not establish accounting correctness.

This is a prevention checklist, not a claim that the failed reconciliation in the reviewed conversation was successfully repaired.
