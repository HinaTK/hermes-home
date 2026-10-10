# Theme rotation and whole-theme grid failure

## Why same-theme comparison can fail

A fund can be the best member of a weak theme while still being a poor grid candidate. Diagnose the theme before replacing one ticker with another:

- **Narrow range:** the common theme's 20-session range does not cover the configured grid gap.
- **One-way trend:** few completed buy→sell cycles because price only rises or falls.
- **Common shock/crowding:** all members show simultaneous cycle drought or inventory stress.
- **Execution problem:** apparent volatility exists, but spreads, liquidity, or T+1 inventory make it unusable.

## Two-level weekly screen

1. Same-theme screen: compare the current baseline with eligible peers using the same trailing common window, normally 63 sessions / roughly three months.
2. Cross-theme screen: compare a fixed, pre-declared candidate set from unrelated themes (for example broad index, coal, industrial metals, media). Do not select the winner after seeing results; record coverage and missing-data counts.
3. Use one standardized 2% grid definition unless the user explicitly changes it. Count completed buy→sell cycles, not touches, alerts, resting orders, or close-only threshold crossings as real fills.
4. If the production dataset is daily-close proxy data, label it as a proxy. It cannot prove intraday execution, order priority, T+1 availability, or broker fills.
5. A cross-theme candidate is only a research lead. Require two consecutive weekly leads by the same candidate, then review net spread after the confirmed fee rule, average inventory cost, downside inventory loss, liquidity, tracking quality, and correlation with the unchanged ETF.
6. If no candidate clears the evidence gates, keep cash and the current authorized policy. Do not rotate merely to increase the apparent cycle count.

## Migration guardrails

An authorized migration and a research rotation are different states. Keep the source in exit-only mode and preserve the target migration unless the user revises it. A cross-theme screen must not automatically cancel, rebase, buy, or undo the target migration. Before any new target activation, reconcile broker orders, fills, frozen cash, T+1 sellable quantity, current quote timestamp, and shared cost caps.

## Suggested report fields

- baseline and authorized migration state;
- same-theme candidate coverage and leader;
- cross-theme candidate coverage, missing symbols, leader and theme;
- common-window sessions and data source;
- completed-cycle proxy counts plus a clear proxy disclaimer;
- consecutive weekly lead count;
- net spread, average inventory cost, drawdown/inventory-loss checks still required;
- decision: continue, research review, or keep cash;
- explicit statement that no order or ledger state changed.
