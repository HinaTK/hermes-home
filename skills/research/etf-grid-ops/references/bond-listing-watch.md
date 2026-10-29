# CN new-listing instrument watch (中签新债/新股 上市提醒)

Class: the user wins an allotment (convertible bond 1手 = 10张 × 面值100, or IPO shares) that has NO market yet, and wants a one-shot reminder when it lists and becomes sellable. The position is OUTSIDE the grid ledger (same as the 159866 buy-and-hold pattern) — no T+1 pool, no 00:01 sync, no grid advice.

## Sizing sanity (user correction — RECURRED, treat as hard pre-check)

First occurrence 2026-10-14 (中鼎转2), recurred 2026-10-26 (中鼎转03) despite this reference existing: the assistant again built a layered hold-then-sell plan and a "多中几手" framing on a 1-lot position. **Before writing ANY advice about an allotment win, state the position size first and derive the decision from it.** A convertible-bond allotment is exactly ONE unit (1手=10张=1,000元) — there is no "多中几手" scenario (that is stock-IPO logic), top-cap subscription ties up no cash (the cap is on nominal subscription quantity, not deposit — never describe it as "押 100 万"). Never build layered strategies (分批卖/留一半赌题材) on a 1-lot position; the entire decision is "wait for listing, sell day one, ~30 seconds". State expected profit per lot (+150~250元 typical) honestly and move on.

## Proven pattern (2026-10-26, 中鼎转03 sz127119)

1. **Identify the code + exchange prefix.** Tencent `qt.gtimg.cn/q=<prefix><code>` works for SZ convertible bonds (`sz127119`). Verify once in the foreground that the vendor returns the placeholder before scheduling anything.
2. **Placeholder detection.** Before listing the vendor returns `last=100.000` (face value), `high/low=0.000`, and a non-listing timestamp. The placeholder is NOT a quote — never compute P&L from it.
3. **Listing rule.** Listed today := quote timestamp is today (`YYYYMMDD` prefix matches, HHMM ≥ 09:00) AND (`last != 100.000` OR `high > 0`).
4. **Script shape (watchdog).** Quiet until listing: empty stdout sends nothing (`no_agent` cron). State file stores `listed` date + `first_quote`; after one alert, self-suppress via state — do not disable the cron from inside the script.
5. **Cron cadence.** Trading days, three ticks (9:10 / 10:10 / 14:10). Listing is a discrete event; do not burn a per-minute job. Job id and script path belong in the memory entry so the task can be paused after the user sells.
6. **Alert content.** Current price/high/low + vendor timestamp + hands held + "check the broker app to sell" + T+0 note (convertible bonds trade T+0 on listing day). SZ convertibles have listing-day intraday halts (20%/30% rules) — mention if relevant.
7. **Market expectation.** Search public analysis for the expected listing range (中鼎转03: 127–130 expected, ~270–300 profit per 手) and include it in the setup reply, explicitly labeled as market expectation, not a promise.
8. **Lifecycle.** After the user confirms they sold, pause/remove the cron job — no zombie monitors.

## Instance artifacts

- Script: `HERMES_HOME/scripts/bond_zhongding03_monitor.py` (self-contained: fetch → placeholder check → one-shot alert → state dedup).
- Cron: `6320900a58dd` (交易日 9:10/10:10/14:10, deliver=feishu, no_agent).
- State: `HERMES_HOME/cache/grid-account/bond-127119-monitor.json`.

## Verification recipe (used at setup)

- Real pre-listing run → exit 0, empty output (correct silence).
- Mock listing-day quote (e.g. last=127.500) → alert fires once, state written; second run silent. Clean the test state file afterwards so live monitoring is unaffected.