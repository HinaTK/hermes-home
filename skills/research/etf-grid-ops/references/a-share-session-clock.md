# A-share cash session vs grid tickets

## Why 09:10 is not a fillable price

User correction 2026-09-23: “明天9:10你给我建仓建议，但是9:10都还没竞价结束，无法保证能用你建议的价格入手.”

- 09:10 is **before** 09:15 call auction.
- Vendor last at 09:10 is almost always **previous close**, not an open.
- Locking that print as a limit (and sizing lots off it) is a false executable ticket.

## Executable moment

Continuous trading starts 09:30. Ops send at **09:32** so the quote timestamp can be ≥ 0930. Recast quantity from live last against remaining cap / 100-share lots / cash floor.

If Tencent field 30 is missing, not today, or HHMM < 0930: emit preview, empty actions.

## Quote check (Tencent `qt.gtimg.cn`)

Split `~`. Index 3 last, 4 prev close, 5 open, 30 datetime. Open at 09:10 is often empty or equal to prev close — still not a continuous fill.

## Do not mix with research engine

Daily-bar research uses previous-close signal / next-open fill. That is a **model**, not a 09:10 WeChat order. Live tickets must not inherit that shortcut.
