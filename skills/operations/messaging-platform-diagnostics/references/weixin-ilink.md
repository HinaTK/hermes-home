# Weixin/iLink evidence notes

## Validated implementation path

The Hermes runtime exposes a standalone send command that reuses the managed profile configuration without requiring an LLM turn:

```text
hermes send --to weixin --json "<short test message>"
```

On Windows desktop installs, invoke the managed runtime executable if the `hermes` launcher is not on PATH, and set `HERMES_HOME` to the managed Desktop profile. Never print the resulting environment or credential contents.

## What a result means

- JSON `success` / provider message identifier: outbound request accepted; still distinguish accepted from user-visible receipt if the provider semantics are unclear.
- `Gateway is not running`: local lifecycle problem; start/restart the managed gateway from the desktop UI.
- `iLink sendmessage rate limited; cooldown active`: provider-side send rejection. Do not treat this as a QR, allowlist, or token diagnosis; do not rapid-loop retries.
- Adapter `connected` alone: only platform-session evidence; it does not prove outbound delivery.

## Reproduction discipline

1. Check the desktop gateway status.
2. If running, make one short proactive-send attempt.
3. If rate-limited, wait at least the provider-reported cooldown and perform no more than one retry.
4. Read back the gateway log for a concrete Weixin inbound/outbound event, while redacting all identifiers in any user-facing report.
5. If no success evidence exists, report the test as unverified/failed and direct the user to **检测连接** or **重新扫码** rather than claiming success.

## Session lesson

A Weixin gateway can restore a saved context and report connected after Hermes restarts, while the standalone proactive send still fails with an iLink cooldown. These are separate states and must be reported separately.
