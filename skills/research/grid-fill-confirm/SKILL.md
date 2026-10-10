---
name: grid-fill-confirm
description: "Use when WeChat reply is 成功 or 失败 for the grid ticket."
---
# Grid fill confirm

As of 2026-09-28 grid notifications and fill replies use Feishu DM, not WeChat.

- For a ticket with several actions, a bare `成功`/`失败` is ambiguous: do NOT run `grid_weixin_confirm.py`, which applies the whole ticket. Identify the exact code, buy/sell, quantity, actual execution price (ask only for missing fields); book that one action idempotently in `grid_account.py`'s ledger, archive/replan the pending ticket, and verify ledger + current ticket.
- If the pending ticket has exactly one action and the user's confirmation unambiguously refers to it, use `python "D:/Hermes Agent CN Desktop/data/hermes-home/scripts/grid_weixin_confirm.py" 成功` (or `失败`) and verify the updated ledger.
- Distinguish a placed limit order from an executed fill. Do not silently count all ticket actions as filled; same-day new buys are T+1. Do not swap tickers or add extra grids.
