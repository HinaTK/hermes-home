# Cross-session continuity: one-way ETF markets

## Confirmed historical evidence

Original session: @session:default/20260922_141141_e5b6cb.

- Message 4354: assistant acknowledged that the old three-close review could leave a single ETF in cash for longer than three sessions after sustained rises. User then requested improvements (4355).
- 2026-09-29 historical follow-up: participation floors of 9,100 shares for 159992 and 4,600 for 159363; early review near base plus one cell; consideration of an upward rebase after a close above the last confirmed sale by 2%, above a rising 20-day average and not overheated. Reported historical tests are not current-runtime verification. These are dated parameters, not instructions to restore them; 159992 subsequently moved to exit-only migration.
- Message 5332: explicitly discussed persistent declines, buying without selling and locked capital; evaluating suspension of new purchases, a lower trading interval, reduction or replacement. It distinguished a temporarily lower range that still supports profitable cycles from a deteriorating instrument. It also admitted the full downtrend diagnosis/rebase/rotation system was not implemented at that time.
- Later rotation discussion in @session:default/20260921_202721_7a359fad, messages 6186 and 6190: few completed cycles can reflect narrow range, rising-market failure to rebuy, falling-market failure to sell, or execution constraints. Candidate leadership is a manual-review signal, not automatic rotation authorization.

## Reusable retrieval procedure

1. Search the user's literal wording, then the operational mechanism rather than only the phrase 单边行情.
2. Prefer original user/assistant messages over compressed summaries. Read the context around a strong hit; verify whether the assistant proposed a rule or the user accepted it.
3. Record source session/message handles alongside a concise durable summary when continuity failed repeatedly.
4. Reply: “聊过；原来讨论的是…；这是历史讨论，当前实现尚需单独核验。” Acknowledge a previous incorrect denial directly.
5. If evidence remains incomplete, state the retrieval limit. Do not infer absence of discussion, broken memory, or current implementation.

## Avoid scope creep

A history question does not authorize ledger edits, order changes, parameter restoration, or a full strategy rewrite. Offer or perform those only when separately requested. This reference records reliable retrieval evidence, not an endorsement that the historical trading rules are optimal.
