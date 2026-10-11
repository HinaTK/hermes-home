# Per-holding pair review (2026-10-11 agreed design)

User approved changing weekly monitoring from a single 589720 hurdle to separate comparisons against each active holding (159363 and589720).159992 remains authorized exit-only and is not a new rotation baseline.

One research simulation only. Weekly consumes full/early/late/recent20 metrics. Two review routes: verified same-index/theme improvements and verified cross-theme rotation. Index/theme classification needs issuer/index primary source evidence; names/correlation alone do not prove same theme. Unknown classification is observe-only, no formal trigger.

Initial, not optimized decision rule: full_cycles and full_cycle_net_per_avg_cost_pct strictly exceed the particular holding; recent20_cycles and recent20_cycle_net_per_avg_cost_pct must not be worse. Midterm-only leaders with recent weakness are observation, not priority. Report early/late cycles, unclosed inventory, capital occupancy, correlation to holdings retained; do not silently use short-term floating loss or MA position as hard rejection.

Persist new versioned pair-specific state for holding/candidate/route. Adjacent distinct valid ISO weeks only; same-week reruns idempotent, candidate/coverage/filter/taxonomy/method changes reset; offline/smoke/custom/history never inherit production state. Degraded runs still show sound pair comparisons but cannot advance/trigger. No broker action or ledger edit.

Temporary Hong Kong-name filter must be disclosed and configurable; never alter qualification universe/trading permissions. Preserve manually verified taxonomy gaps in report. Updating code is not proof of cron delivery. Verify real saved-result replay and production wrapper, protected trading-file hashes, independent review, tests before commit/push explicit files only.
