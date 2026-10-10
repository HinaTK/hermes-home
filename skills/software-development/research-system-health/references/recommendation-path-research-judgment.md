# Judge the official path as research, not alpha

Use when the user asks 怎么看推荐路线 / 投资研究员观点 on `stock_recommend` (AH_analyse official path). Code-health audits still follow the main SKILL.md sequence.

## Verdict shape

One line first: **honest observation workflow until P0 tickets; still unproven as edge.** Then table: layer → actual behavior → investment meaning. Separate 看多 (process) from 看空 (not a thesis).

If the user says they use the push **to buy**, switch frames: judge the **buyable standard**, list gaps, do not lecture 观察候选. Do **not** mint a personal BUY from a WATCH JSON.

Do not treat a quality-gate pass as edge.

## What the official path actually is

`stock_recommend`: snapshot (prefer previous-close before open) → explainable composite → `select_by_rules` → 0–3 formal **CONDITIONAL_BUY** (RR≥1.5 + position) → quality gate → Feishu → 10:00 `open_confirm` → `BUY` or `CANCEL`.

Default composite (`candidate_pool.DEFAULT_WEIGHTS`): trend 0.25, price_volume 0.20, value_quality 0.15, capital 0.15, relative_strength 0.15, event 0.10, plus a small risk penalty. Hotspot bonus caps at 0.015 and must not become the rationale.

Pre-market card: CONDITIONAL_BUY + zone/stop/target/position + 开盘确认前不得成交. Open-confirm card: 可下单 or CANCEL. Scaled `confidence` is still not a win rate. See `references/execution-ticket-p0.md`.

## Do not call these edge

| Artifact | What it is |
|---|---|
| `confidence` | `0.45 + composite × 0.4` scaled magnitude |
| Formal pick rationale | 60d momentum, RS vs benchmark, turnover, PE filter, main-net flow — not a company thesis |
| Buy/stop/target | Support / resistance / ATR×1.25 geometry |
| T+1/3/5/10 ledger | Fixed-horizon fill; `execution_validation` does **not** simulate CONDITIONAL_BUY → open confirm, stops, or capital constraints |
| Event factor 0.5 | Placeholder when news is missing; still can count toward “3 dimensions” |
| `recommendation_contract` | `build_decisions` / `constrain_portfolio` written alongside; Feishu ranking is `select_by_rules` |

Empty book is a **legal** research output (`data_insufficient` / `awaiting_confirmation` / `screened_out`). Collapse of empty-book rate in a defense regime is a process-falsifier.

## How a researcher would use it

| Use | Rating |
|---|---|
| Pre-market regime / offense vs defense | Usable for risk budget |
| 0–3 CONDITIONAL_BUY names | Draft tickets only until `open_confirm` |
| Open-confirm BUY | The only send-time buy; still unproven edge |
| Composite / confidence | Not a win rate |
| Hit rate / weekly reweight | Unproven until independent baseline + trigger-aware execution |

Defense regime from benchmark MA can coexist with a high `market.score` from breadth/hotspot heuristics. Say which layer you trust; do not average them.

## Falsifiers of the *process* (not of a stock)

- Previous-close scan labeled as intraday strength
- Quality failure still pushing a formal CONDITIONAL_BUY/BUY card
- Pre-market card printed as market BUY (missing 开盘确认前不得成交)
- Advertising T+N hit rate without simulating open-confirm / CANCEL
- Defense sessions still filling the formal slot every day
- Event placeholder 0.5 counted as an independent confirming dimension
