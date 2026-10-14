---
name: grid-fill-confirm
description: "Use when WeChat reply is 成功 or 失败 for the grid ticket."
---
# Grid fill confirm

As of 2026-09-28 grid notifications and fill replies use Feishu DM, not WeChat.

- For a ticket with several actions, a bare `成功`/`失败` is ambiguous: never apply the whole ticket. Identify exact code, buy/sell, quantity and actual price (ask only missing economic fields). User rule 2026-10-14: default date is the Beijing date of the original confirmation message, and execution IDs must auto-increment per ETF; do not ask user to invent IDs. Always reuse original message identity/time for retries, with a distinct item key for multiple fills in one message. Until the default interface is verified deployed, pass these internal fields explicitly; never assume code changed from a promised implementation. For confirmed 589720/159363, use the deployed unified state entrypoint, not legacy grid_account.apply/ledger. Verify exact state and immediately print refreshed suggestions; touch or order placement is not execution.
- The legacy whole-ticket `grid_weixin_confirm.py 成功` command is unsafe and must not apply inferred fills. Deployed unified syntax (verify --help first): `python "D:/Hermes Agent CN Desktop/data/hermes-home/scripts/grid_weixin_confirm.py" 成功 --code sh589720 --side buy --qty <actual_qty> --price <actual_price> --date YYYY-MM-DD --id <stable_execution_id>`; for 159363 use `sz159363`. Verify the exact confirmed state file and immediately print new recommendations. Bare 成功 is rejected; 失败 does not mutate trades. Never substitute guessed dates or new IDs for a retry.
- Distinguish a placed limit order from an executed fill. Do not silently count all ticket actions as filled; same-day new buys are T+1. Do not swap tickers or add extra grids.
