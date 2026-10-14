---
name: messaging-platform-diagnostics
description: "Use for Hermes messaging diagnostics."
version: 1.0.0
metadata:
  hermes:
    tags: [messaging, gateway, weixin, feishu, onboarding, diagnostics, delivery]
---

# Hermes Messaging-Platform Diagnostics

Use this skill for failed onboarding, missing inbound messages, failed outbound delivery, and questions about whether the Hermes gateway must be started after restart.

## Operating principles

1. **Protect secrets.** Never display, request, reconstruct, or paste tokens, cookies, secrets, full user IDs, open IDs, or account identifiers. Report only redacted status and non-sensitive evidence.
2. **Separate layers.** Diagnose in this order:
   - Gateway lifecycle: running/stopped, startup completion, crash/restart history.
   - Platform connection: provider adapter connected, provider endpoint reachable, context/session restored.
   - Policy/routing: allowed-user list, home channel, DM policy, target resolution.
   - Delivery: actual inbound event or actual outbound send result.
3. **A connected adapter is not proof of delivery.** Require a concrete inbound log event or a successful outbound result/message ID. Do not describe a connection check as a successful push test.
4. **Use the desktop UI first.** For insufficient evidence, ask the user to click **检测连接** or **重新扫码** in the onboarding page; avoid complex shell commands.
5. **Keep actions bounded.** Give no more than three next steps, and make each executable in the desktop app or provider console unless the user explicitly asks for technical investigation.

## Platform-specific triage

### Weixin / iLink
Prioritize, in order:

1. Gateway is actually running, not merely configured. The normal post-restart behavior is automatic startup; the user should not need to click start on every Hermes launch. A transient `stopped` diagnosis during startup is different from a persistent failure.
2. QR state only when onboarding evidence shows it is relevant: expired QR, scan not confirmed, or credentials not returned. Do not ask for a new QR scan just because a connected adapter has not yet been delivery-tested.
3. iLink connection and send path. Confirm the adapter reports connected to the iLink endpoint, then test one bounded send. Treat provider rate-limit/cooldown as a provider delivery failure, not as an onboarding or allowlist failure.
4. The scanned user is in the allowed list and home channel. Report only that the lists are configured; never expose their full identifiers.
5. Gateway restart after onboarding or configuration changes. A restart should restore a saved Weixin context when available; re-scan is a fallback, not the default.

When testing a proactive message, use the configured home target and capture the machine-readable result. A result such as `success` with a provider message ID is evidence of delivery initiation; `rate limited` or `cooldown active` is not success. Do not loop rapidly: wait and perform at most one bounded retry, then surface the provider error.

### Feishu
Prioritize application publication, bot capability, message event subscription, send/receive permissions, and the allowed-user list. Verify both inbound and outbound evidence separately.

## Restart semantics

Saved platform configuration and credentials should survive an ordinary Hermes restart. The gateway process must be running for inbound processing and scheduled delivery. If the desktop app starts the managed gateway automatically, no manual start is expected after every restart. If status remains stopped after startup settles, use the desktop **保存并启动网关**, then **检测连接**; do not rotate secrets first.

### Validated manual restart path (Windows desktop)

When the desktop UI restart button is unavailable or the gateway remains stopped, the following path was validated on 2026-10-14:

1. Confirm the gateway is actually stopped: `ps aux | grep hermes` returns nothing, and `gateway.log` shows no active control pipe.
2. Launch the managed runtime directly with `--replace` to force a new instance:
   ```cmd
   "D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18\hermes-agent-cn-runtime-win32-x64.exe" gateway run --replace
   ```
3. Tail `logs/gateway.log` and confirm the startup sequence: platform connections → `✓ feishu connected` / `✓ weixin connected` → `Gateway running with N platform(s)`.
4. Verify the new start timestamp in `gateway-starts.log` (root of `HERMES_HOME`, not `logs/`).

The `gateway-service/Hermes_Gateway.cmd` and `gateway-service/Hermes_Gateway.vbs` wrappers set the required environment variables (`HERMES_HOME`, `PYTHONIOENCODING`, `HERMES_GATEWAY_DETACHED`, `HERMES_SUPERVISED_CHILD`, `VIRTUAL_ENV`, `PYTHONPATH`) and invoke the same runtime — use these for a service-style launch instead of the bare exe.

### Periodic unclean exit pattern

On Windows desktop, the Hermes gateway has been observed to die at irregular 2–6 day intervals with `previous_unclean_exit` in `logs/gateway-exit-diag.log`. The lifecycle ledger consistently shows `state_db_integrity: ok` and `suspected_oom: false`, which classifies these as **external kills** (SIGKILL, VM death, Windows-level termination) rather than Hermes crashes. No traceback or exception is found in `errors.log` within the window between `last_heartbeat_at` and restart.

When this pattern is present:
- Do not open a bug report or rotate credentials — the state is clean, the process was killed externally.
- Recommend checking Windows Event Viewer for process-termination events, or using the `.vbs` wrapper for more resilient service-style supervision.
- After restart, verify both platform connections independently; do not assume Weixin health from Feishu health or vice versa.

## Evidence language

Use precise status labels:

- **Configured:** required settings are present (redacted).
- **Connected:** adapter established a provider connection.
- **Gateway running:** the local gateway completed startup.
- **Inbound verified:** a real user message reached Hermes.
- **Outbound verified:** a real send returned success/ID.
- **Unverified:** no concrete message event or send result exists.

Never infer outbound success from a connection log. If a send attempt fails, state the exact non-sensitive failure class and avoid claiming the user received anything.

## References

- Weixin/iLink reproduction and evidence notes: `references/weixin-ilink.md`
- Gateway lifecycle and Windows restart evidence: `references/gateway-lifecycle-windows.md`
