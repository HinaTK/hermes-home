# Pair comparison reporting and validation

## Legibility acceptance criterion

User corrected a report that named both same-class and cross-theme priority candidates without comparing their counts against current holdings. Always produce one row per holding/route/candidate:

| Route | Holding → candidate (codes + names) | Full cycles holding → candidate | Signed gap | Recent20 holding → candidate | Signed gap |
|---|---|---:|---:|---:|---:|

Read the same saved research result for both sides; calculate differences programmatically, not mentally. Report counts as integers, money with two decimals, efficiency with explicit denominator/percent units. State shared full-window dates, recent-window length, model assumptions, and simulated rather than actual fills. When recent counts tie, explicitly say the candidate has no recent count advantage. Do not equate priority selection (which also tests capital efficiency) with dominance in all operational measures.

Illustrative dated 2026-07-07→2026-10-09 run, not reusable current recommendations: 159363→159246 full15→19 (+4), recent5→5 (0); 159363→589120 full15→38 (+23), recent5→10 (+5); 589720→589120 full34→38 (+4), recent9→10 (+1). Cross-theme589120 retained589720 correlation≈.998 flagged concentration, not complementarity. Refresh data before any new recommendation.

## Official taxonomy and identifiers

- Validate entry dictionaries, verified boolean, nonempty list of valid HTTP(S) source URLs; malformed strings/null entries are unknown and excluded from verified coverage. URL validity checks schema, not truth of official evidence.
- Verify source content independently before treating child claims as proven. A JSON file parsing successfully is not evidence verification. Preserve uncertain entries as pending rather than invented facts.
- Lookup explicitly supports six-digit and exchange-prefixed aliases while preserving original output identifiers. Exclude all aliases of live holdings before selecting candidates; otherwise a holding can win its own replacement comparison.
- Same-index fallback: exact official index_name match when at least one ID is missing; conflicting nonempty IDs must not fall back to names. Ambiguous prefixed lookup fails closed.
- Fine-grained theme differences do not establish diversification. Show correlation/retained exposure warning without inventing a hard gate not agreed by the user.

## Regression and completion

Tests: malformed/null entries and coverage; candidate/baseline NaN/±Infinity; missing/full-window gates; bare/prefixed holding exclusions; official exact-name fallback and ID conflict; unknown observe-only; pair state isolation, adjacent weeks, idempotence and candidate/coverage/taxonomy/filter resets; degraded no-write/no-trigger.

Verify genuine saved-result replay and production wrapper separately. Replaying cached data is not a fresh online fetch. Keep replay states isolated and protect account/trading file hashes. Independent reviewer must inspect a stable final snapshot, not implementation-in-flight failures. Late asynchronous messages are historical evidence: reconcile them against final tested artifacts and do not undo completed fixes or restart already-completed work merely because an older notification arrives. If response is needed, briefly distinguish snapshot from final result; avoid repeating a full completion report for every delayed notification.
