# Completed-round-trip ranking delivery

## Correction motivating this rule
The user repeatedly requested top ten by completed cycles. Delivering the complementary score top ten, then attaching each score-ranked row's cycle count, still failed the request. A filtered shortlist was empty even though the saved full ranking had valid cycle counts. The durable correction is the ordering and scope, not a particular week's winning ETF.

## Reuse a completed run
1. Identify the exact saved result for the run being discussed; do not launch a fresh research run merely to sort its results.
2. Select rows with complete four-window coverage and finite full_cycles/full_cycle_net. Deduplicate codes; validate eligible count.
3. Default count leaderboard includes holdings. Preserve explicitly requested category exclusions and disclose them. Do not inherit a separate shortlist's exclusion of holdings or baseline superiority gate.
4. Sort `(-full_cycles, -full_cycle_net, code)` programmatically. Take ten, assert row count where at least ten are eligible, and print code/name/cycles/net spread. Scores are not the primary ranking key.
5. Locate holdings in this exact same sorted population if their ranks are mentioned. Equal cycle counts use the disclosed tie-break; ordinal positions are not shared ranks.
6. Report common window, coverage failures, simulation parameters/basis and exclusions. Net spread from closed cycles excludes open inventory P&L and is not actual account return.

## Three distinct outputs
- Universe completed-cycle top ten: includes holdings by default; requested primary answer.
- Baseline-beating rotation shortlist: excludes holdings, may be empty; supports review, not automatic trading.
- Complementary score ranking: multi-factor view; only provide when requested or clearly secondary.

## Regression acceptance for report changes
Use a fixture where the highest-cycle ETF is a holding, no candidate beats it, and the highest-score ETF has fewer cycles. Assert the count leaderboard is nonempty, the holding remains first, the score leader does not displace it, and the empty shortlist is separately labeled. Include deterministic tie-break and names. Follow Superpowers debugging/TDD for code changes; a chat-only re-sort does not mean the production report was repaired.
