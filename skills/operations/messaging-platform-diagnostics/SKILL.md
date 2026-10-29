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

### Provider errors delivered through a healthy messaging channel

When the bot replies “The model provider failed after retries”, distinguish model execution from messaging transport before changing platform settings. Correlate the screenshot timestamp with inbound events and provider errors in the active managed profile's logs. An inbound event followed by a provider HTTP error identifies the failed layer; it does not justify re-scanning, changing mention policy, or rotating platform credentials.

- Capture the actual provider/base URL/model tuple from the failing gateway request. A working Desktop chat may use a different tuple; its success does not validate the messaging gateway's model route.
- Answer "which model is answering NOW" from the newest per-turn evidence — the latest `conversation turn:` or `switch_model` log line for each surface (desktop vs gateway). Lead with current state, history second; the user asking "现在" does not want a root-cause narrative first. Log lines from an earlier failure window are not the present, and config.yaml mtime is not per-surface state. When the runtime's own metadata banner says the active model changed mid-session (e.g. to `gpt-6.1-sol`), trust the latest banner over the turn-context line captured at turn start — a turn can start on a routing group and finish on a concrete model.
- **Session-level vs global model switching (2026-10-22 case):** Desktop Cmd+K / Win-key model switches are SESSION-ONLY — they never write config.yaml, so the Feishu gateway keeps serving the global default while the desktop appears to follow the user's choice. Symptom: user says "我不是改成X了吗". Fix for real unification: `hermes config set model.default <model>` + `hermes config set model.provider <provider>` then read back — setting provider also clears the old provider's base_url automatically. A gateway restart is required afterwards for the running process to pick it up (user may decline the restart; then state plainly that the running gateway still carries the old config).
- Model routing groups (e.g. `group/smart-split` on a local proxy) select a member per request and do not expose which member answered — logs record only the group id. Attribute a reply to a named member model only with per-request evidence; otherwise say the member is not identifiable, neither blaming nor exonerating a specific model.
- Enumerate live ids via the proxy's `/v1/models` (routing groups and models are listed together) before judging a model id valid or stale — a 404 "knows no model" means the id/route no longer exists on that proxy.
- If the user already exchanged messages after the failure window, later real inbound + successful outbound turns are the cheapest recovery evidence — prefer them over sending a test message.
- A model-not-found HTTP 404 is a routing/identifier failure, not evidence of a timeout, insufficient balance, or a disconnected Feishu adapter. Do not blindly retry or substitute an apparently similar model ID.
- Bound log extraction by timestamp and error category, filter BEFORE printing, and redact secrets and user/chat identifiers. Avoid broad keyword dumps that overflow the capture window and bury the root error.
- Separate **cause identified** from **repair verified**. Only claim recovery after the intended configuration has been read back and an ordinary message has completed an actual model turn and reply.
- Never replay a trade confirmation or other state-changing instruction as a messaging test. Use a harmless greeting, and check the authoritative state before retrying any business action across surfaces.
- **Provider-failed messages are persisted and retried (2026-10-22):** when the model provider fails mid-turn, the gateway persists the inbound user message (log: “Transient agent failure … persisting user message so conversation context is preserved on retry”), so the SAME confirmation text can arrive again after recovery. Before booking a re-delivered trade confirmation, query the authoritative ledger for an existing record with the same code/side/qty/price: if one exists, confirm with the user whether this is a new round before registering anything — neither blind duplicate-booking nor silent dropping. (Case: F买10,000@0.797 matched already-booked 020; verified as a new round → booked as 024.)
- **Routing-group latency is a user-visible symptom worth reporting proactively (2026-10-23):** a local-proxy routing group (`group/smart-split`) showed 57–121s turn latencies and a direct probe that did not return within 60s. When the user asks why replies are slow/dumb while using a routing group, check per-turn latency in agent.log and attribute behavior to the group (member not identifiable per-request), not to a specific member model. Enumerating `/v1/models` confirms the group id exists (a stale member id like `auto/gpt-6.1-sol` 404s while the group itself is fine).

See `references/provider-route-diagnosis.md` for a diagnostic case and evidence boundaries; it is not a validated repair recipe.

### Health-check false alarms and notification boundaries

When the user says “修复报错，不要再发飞书”, stop the **specific offending monitor's delivery** first: list jobs, identify the exact job ID from the screenshot, update its delivery to `local`, then read back that job. Keep the monitor running locally; do not disable unrelated trading reminders or send a test message to the channel the user just asked to silence.

**Duplicate monitor jobs → merge, don't coexist (2026-10-26 user rule: “我只要一个，目的就是保持网关活着并且不异常").** When two cron jobs overlap in purpose (e.g. a Feishu health check + a gateway auto-heal both watching the gateway), do NOT offer a menu of coexistence options — the user wants ONE job. Merge into a single watchdog script with one cron: (1) process dead → auto-restart, restart outcome pushed (this fault MUST alert every time); (2) config drift that makes Feishu silently swallow messages (GROUP_POLICY=disabled / REQUIRE_MENTION=true / channel dir missing) → diagnose-only, pushed with same-fault-same-day dedup (state file keyed by fault fingerprint + day) so a persistent fault reminds once per day, not every 5 minutes; (3) healthy → exit 0, print nothing. Remove BOTH old cron jobs and deploy the merged one; verify by mocking each fault branch (config-drift first push / re-run silent, recovery clears state, dead-process restart path) plus a real run returning exit 0 silently. Instance: `scripts/gateway_keeper.py`, cron `072047b92c2d` (*/5min, deliver=feishu).

For code changes, use the user's preferred Superpowers workflow: load systematic-debugging and test-driven-development, reproduce the exact symptom with a failing test, fix the cause, run regression tests and the actual deployed script. Verify exit code AND stdout/stderr explicitly; a successful piped shell command alone does not establish test success.

**Missing startup logs are not a disconnection signal.** Connection markers can rotate into old files or leave the last 100 lines while the adapter remains active. Recent group-message events are activity evidence, not proof of current transport health or outbound delivery. Missing/stale logs must be labeled **unknown/unverified**, not “disconnected”, and must not trigger blanket policy changes or a gateway restart. Retain independent process/config checks. Do not report unknown as positively healthy in prose, even if an advisory check is non-fatal.

See `references/feishu-monitor-log-rotation.md` for the regression recipe and deployment verification.

### Feishu policy drift (silent config regression)

**Partial silence is the signature symptom**: DM works, group chat doesn't. When this pattern appears, check `.env` directly — do not trust the onboarding diagnosis JSON snapshot, which may be stale:

- `FEISHU_GROUP_POLICY=disabled` → group messages silently dropped
- `FEISHU_REQUIRE_MENTION=true` → only @-mentions trigger a response

Fix with `sed` on `.env` and restart the gateway. No credential rotation needed.

**Stale PID file on restart**: `gateway-runtime/gateway.pid` lives outside `HERMES_HOME` and can survive profile switches. If a restart fails with `PID file race lost to another gateway instance`, delete the stale file first. See `references/feishu-policy-drift.md`.

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
