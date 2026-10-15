---
name: hermes-operational-diagnostics
description: "Use when diagnosing Hermes health."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, diagnostics, gateway, messaging, memory, openviking, model-routing, windows]
---

# Hermes Operational Diagnostics

Use this class-level skill when Hermes appears to have stopped responding, a desktop restart is suspected, messaging delivery is questioned, or persistent memory may be unhealthy.

## Core principle

Do not collapse these into one status: desktop UI alive, runtime/gateway alive, adapter connected, inbound received, model request succeeded, outbound sent, memory configured, provider healthy, memory activated, and functional memory operation passed. A green result at one layer never proves the next layer.

## Required workflow

### 1. Establish the runtime boundary

Identify the active Hermes home from the managed desktop environment. Inspect processes, listening ports, recent logs, and Windows Application Error / Windows Error Reporting events when a crash is suspected. Capture exception code, module, version, offset, and timestamp. Classify the event as desktop native crash, gateway/runtime exit, adapter disconnect, model/API failure, UI-only failure, or persistent-state/database issue.

Do not call a model error a channel outage, and do not call a desktop crash an OpenViking failure without evidence.

### 2. Verify message channels with a delivery chain

For each channel independently, seek: adapter connection/startup; inbound adapter record with message id and chat id; gateway inbound dispatch; model request/result; outbound send; provider acknowledgement if available.

Report the last confirmed stage. “Feishu inbound and outbound are confirmed, but model generation failed” differs from “Feishu is down.” Absence of a log line is only “not verified” unless the observation window and expected traffic are known. Never infer WeChat health from Feishu health.

### 3. Verify model routing separately

Record the effective provider and model from logs, not only the configured default. Check in-place model switches, fallback providers, auxiliary/compression providers, and route compatibility. A model accepted by a custom provider may be rejected by OAuth/Codex. Treat HTTP 400 model-unsupported errors as routing failures, not messaging transport failures.

### Session-scoped model changes: scope and evidence

When the user requests a model change for the **current conversation**, distinguish a live session hot-swap from a default-model configuration update. Do not change global/profile defaults as a substitute. Inspect the installed interface's documented operation and scope before writing; a model-setting endpoint can explicitly apply only to new sessions.

A provider's display label is not a model identifier. Resolve the exact provider/model pair from an authenticated catalog or the actual picker before supplying a command. Never manufacture a slash-command argument by concatenating provider and model names. If the identifier is unverified, direct the user to the picker by the exact display label rather than offering a plausible executable command.

After any successful switch operation, read back the effective **target session** provider/model; reading the configured default is insufficient. A later runtime model-change notification is also evidence. Until then, report the switch as unverified or not completed, not successful. Do not turn unsuccessful control-interface attempts into a reusable workaround, and do not restart the user's app simply to expose a control port.

### Authenticated provider but missing picker model

When a user says they already authenticated but cannot find a model, investigate before telling them to select it again. Do not send them back to the same picker without checking its actual contents. Verify three distinct layers: provider authentication in the active managed home; the authenticated live model catalog; and the picker-returned model list. Authentication does not imply the picker exposes the entire catalog. Curated lists, tier filtering, and separately named free variants can explain a mismatch.

Preserve exact model IDs and suffixes such as `:free`; do not silently substitute the free variant for the requested ordinary variant. A local cache is supporting evidence, not proof of present availability or entitlement. A parser accepting a switch command proves syntax only, not inference access or a completed session change. Report those boundaries explicitly.

See `references/provider-catalog-picker-mismatch.md` for the verified Nous catalog/picker diagnostic technique and evidence limits.

### 4. Verify memory in four independent layers

Check: (1) `config.yaml` provider, endpoint, account, user; (2) provider process health and version; (3) Hermes activation logs showing registration/activation; (4) a real search/read or safe write-then-read operation.

For OpenViking, `http://127.0.0.1:1933/health` is only a service check. A configured endpoint does not prove the server is alive, and a healthy server does not prove Hermes uses it. A successful semantic search is the strongest practical full-path check.

Keep Dashboard API health separate from direct provider health. A dead Dashboard port does not imply the runtime provider is dead, but Dashboard-based memory management is then unverified.

### 5. Check long-session and persistence hazards

Look for context overflow, skipped transcript persistence, failed compression, stale runtime identity, message-alternation repairs, SQLite lock warnings, and orphaned sessions. These can break one conversation while the gateway and channel remain healthy. For repeated compression failures or very large history, recommend a new session rather than calling the channel broken.

## Output contract

Lead with a compact status table. Use `confirmed healthy`, `confirmed failed`, `degraded`, or `not verified`. Include evidence timestamp, exact layer, likely root cause, what is safe now, what remains unproven, and the smallest next verification step. Redact tokens, API keys, cookies, and credential-bearing config lines.

## Gateway lifecycle diagnosis

When Hermes exits unexpectedly, distinguish **external kill** from **internal crash** using the lifecycle ledger. These two files carry the decisive evidence:

| File | Purpose | Key field |
|---|---|---|
| `logs/gateway-exit-diag.log` | Per-process lifecycle record (JSON lines) | `tag: "gateway.previous_unclean_exit"` — appears only when the prior process died without running its exit path |
| `logs/desktop-gateway-restart.log` | Full restart log with preflight summary | `preflight=stop_attempted=…` + `gateway.lifecycle_ledger: Previous gateway life … exited UNCLEANLY` |

**Classification logic:**

- `state_db_integrity: ok` + no traceback/exception in `errors.log` + `suspected_oom: False` → **external kill** (SIGKILL, VM death, Windows-level termination), not a Hermes crash.
- `state_db_integrity: corrupted` or a Python traceback in `errors.log` → **internal crash**.
- `suspected_oom: True` → memory exhaustion; check process memory and `agent.log` for context-size warnings before the exit.

The `last_heartbeat_at` field in the lifecycle ledger tells you the last time the process reported alive. A long gap between heartbeat and restart (e.g. 5+ days) with no error trail strongly indicates an external event (Windows update, reboot, manual close), not a runaway process.

**Practical procedure for an unclean exit:**

1. Read `logs/gateway-exit-diag.log` — the last entry with `gateway.previous_unclean_exit` is the prior process's obituary.
2. Read `logs/desktop-gateway-restart.log` — the `preflight=` line tells you whether the restart wrapper tried to stop the old process cleanly (`stop_attempted=true`) or found it already dead (`stop_attempted=false`).
3. Grep `errors.log` and `agent.log` for traceback/exception/segfault/panic within the window between `last_heartbeat_at` and the restart timestamp.
4. If step 3 is clean, classify as external kill. Do not treat it as a code bug unless there is a crash signature.

## Common pitfalls

- A running process does not prove an adapter is connected.
- Adapter receipt does not prove model completion.
- `response ready` does not prove user-visible delivery; seek send/ack evidence.
- OpenViking health does not prove Hermes memory activation.
- Provider activation does not prove search/read/write works.
- No WeChat log is not proof of failure without expected traffic; report it as unverified.
- A model-switch/fallback line can invalidate a correct static configuration.
- **Do not assume an unclean exit is a Hermes crash.** The lifecycle ledger's `state_db_integrity: ok` + absent traceback pattern is a strong signal of external termination. Check `gateway-exit-diag.log` before opening a bug report.

See `references/verified-layer-checklist.md` for the reusable evidence checklist and model-route/memory verification pattern.
