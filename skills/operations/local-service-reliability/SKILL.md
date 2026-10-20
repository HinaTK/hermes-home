---
name: local-service-reliability
description: "Use when hardening local background services."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [services, supervision, windows, health-checks, lifecycle, openviking, gateway]
    related_skills: [hermes-agent, hermes-memory-providers, messaging-platform-diagnostics, systematic-debugging]
---

# Local Service Reliability

Use this class skill when a desktop agent depends on local background processes such as a messaging gateway, memory server, vector database, browser daemon, or model proxy.

## Core principle

A process being present, a port being open, and `/health` returning success are progressively stronger signals—but none necessarily proves the user-visible feature works. Every recovery must distinguish:

1. **Process layer** — executable exists and the expected process is running.
2. **Transport layer** — the expected port/socket accepts connections.
3. **Service layer** — health and initialization endpoints succeed.
4. **Functional layer** — a safe real operation succeeds (for memory, an actual search; for messaging, an inbound/outbound probe; for a model proxy, a minimal completion).
5. **Lifecycle layer** — startup after login, restart after failure, duplicate-instance behavior, and logs are all verified.

Do not report a service as fully recovered until the functional layer passes.

## Required workflow

### 1. Preserve evidence before changing state

Capture the current process list, service/task definitions, relevant logs, configuration paths, version, and exact error. Do not reinstall or delete data as a first response. Back up configuration before changing provider models, endpoints, or credentials. Never print secrets.

### 2. Separate historical and current failures

A long-running background command may continue emitting old traceback lines after the service has been fixed. Record process/session IDs and timestamps. When a watch-pattern alert fires, inspect the current process log and run a fresh functional probe; do not infer that the newest process failed from an old session's output.

### 3. Trace through the stack

For integration failures, follow the call chain from user operation to dependency. Example: memory search → intent planner → VLM → upstream model endpoint. A healthy local HTTP server can still fail at the upstream model or embedding layer. Test the upstream model list and a minimal completion with the configured model, while redacting API keys.

### 4. Make one controlled change

Change one root cause at a time. For an unsupported upstream model, back up the config, select a model confirmed by the provider's live model list, update both the active config and any generator/template that could recreate the stale value, restart the service, and rerun the functional probe.

### 5. Add supervision without duplicate owners

Before creating a new supervisor, check for existing service managers, scheduled tasks, systemd/launchd units, desktop-managed processes, PID/lock files, and duplicate instances. Prefer the product's native installation command for its own gateway. For an independent local service, use one supervisor with:

- login/startup trigger;
- delayed start when dependencies need time;
- no duplicate instances;
- restart-on-failure;
- bounded readiness polling;
- explicit working directory and environment/config path;
- persistent supervisor logs;
- no destructive data reset.

On Windows, a Scheduled Task is acceptable for interactive desktop services. Configure it not to stop merely because the machine is on battery or idle, unless that behavior is intentional. For long-running supervisors, set no short execution time limit and configure task-level restart behavior.

### 6. Verify after supervision is installed

Verify the task/service definition by reading it back, confirm the task is enabled, run it once, check its result and logs, inspect process ownership, and run the complete functional probe. A task that exits immediately with a nonzero result is not a successful installation even if the task exists.

## Reboot-bound installation checkpoints

For local runtimes that require Windows optional features, distinguish installer success, feature activation, runtime readiness, and functional verification. A successful MSI exit or feature state read-back is not proof the runtime can start. Never reboot automatically without authorization.

When a restart blocks progress, persist a checkpoint outside the application repository: verified completed steps, exact target paths, installer provenance/checksums, actual blocking probe and its exit status, and explicitly unverified remaining work. Report the partial result plainly; do not label the service installed and usable. On resumption, rediscover installed state before importing environments or rerunning installers; do not delete/unregister existing environments to retry. Keep version-specific observations in references, not permanent compatibility rules.

See `references/windows-runtime-installation-checks.md` for verified installer checks and Windows command/output pitfalls. This reference does not constitute a completed Docker installation recipe.

## OpenViking-specific checks

For Hermes + local OpenViking:

- Keep OpenViking in its own virtual environment; do not install it into Hermes Desktop's runtime.
- Set `OPENVIKING_CONFIG_FILE` and `OPENVIKING_CLI_CONFIG_FILE` explicitly when launching the server.
- Check `/health` and `/api/v1/system/status`.
- Then execute a real semantic search through the Hermes/Viking client.
- Treat LDAP optional-plugin warnings as non-blocking only when local `dev` auth is intentionally used.
- A VLM/model failure can surface only during semantic search; a 200 health response does not rule it out.
- If the configured model returns `model_not_found`, query the provider's live `/models` endpoint and test a minimal completion before changing the config.
- Back up `ov.conf`; update any config-generation script as well as the live config.

See `references/openviking-windows-supervision.md` for the validated Windows pattern and failure distinctions.

## Hermes gateway-specific checks

For the Hermes messaging gateway:

- Use the native `hermes gateway install` path rather than adding a second competing launcher.
- Verify the gateway task and current gateway status separately.
- Check platform connection state and real message events separately from model-provider errors.
- Distinguish gateway process failure, platform websocket/iLink failure, outbound send failure, and upstream model 502/stream interruption.
- Do not rotate Feishu/Weixin credentials or reset sessions until logs show an authentication/session problem.

## Health-check noise reduction

Cron-driven health checks should be **silent on success**. A check that prints "all checks passed" every few minutes is not monitoring — it's noise. The script should produce output only when a check fails, and the cron job's delivery should be configured to send only on non-zero exit.

**Pattern:**
```python
if all_ok:
    return 0  # silent — cron has nothing to deliver
print("=== FAILED ... ===")
for line in failures:
    print(line)
return 1
```

**Threshold tuning for idle services:** A service can be healthy but idle. Log-file mtime staleness thresholds must account for this — a gateway that only writes logs on activity may go 15+ minutes without a new line while perfectly healthy. Default stale thresholds should be 30+ minutes, not 5-10. Always verify the process is actually alive (tasklist/PID file) before declaring a log-staleness failure.

**Distinguish idle from dead:**
- Process alive + log stale → idle, not failure
- Process dead + log stale → genuine failure
- Process alive + log fresh → healthy

### subprocess encoding on Windows

Health-check scripts that shell out to Windows commands (`tasklist`, `sc`, `wmic`, `netstat`) via `subprocess.run(..., text=True)` **must** use an explicit encoding appropriate to that command, or capture bytes and decode after inspecting the output. Without it, Python falls back to `locale.getpreferredencoding()` — GBK on Chinese-system Windows — while these commands emit UTF-8. The mismatch raises `UnicodeDecodeError` inside `subprocess`'s `_readerthread`, which crashes the script with a non-zero exit code even though the underlying check may have succeeded.

**For commands verified to emit UTF-8, use:**
```python
subprocess.run(
    ["tasklist", "/FI", "PID eq 1234", "/NH"],
    capture_output=True, text=True,
    encoding="utf-8", errors="replace",  # ← explicit, never rely on locale
    timeout=5,
)
```

Do not assume every Windows executable emits UTF-8: redirected `wsl.exe` output in the observed installation emitted UTF-16LE, producing NUL-filled mojibake when treated as UTF-8. Capture bytes and explicitly decode UTF-16LE when confirmed; other commands may use UTF-8 or the local code page. A PowerShell UTF-8 console setting does not guarantee the encoding of every native child's redirected output.

Explicit encoding selection applies to every `subprocess.run(..., text=True)` in a health-check or cron script, including `git` invocations and gateway-restart commands. Scan scripts with `grep -n "text=True" *.py | grep -v "encoding="` to find stragglers.

The `errors="replace"` fallback is intentional — it prevents a crash on unexpected bytes, and the replaced characters don't affect PID matching or status parsing. Never silently drop the encoding parameter "because it works on my machine"; the locale differs per system.

## What not to do

- Do not equate `available`, `running`, or `healthy` with end-to-end readiness.
- Do not re-use a stale watch-pattern alert as proof of a current failure.
- Do not run two independent supervisors for the same process.
- Do not repair by deleting vector data, resetting credentials, or reinstalling runtimes before preserving evidence.
- Do not capture a transient setup failure as a permanent tool limitation; record the working recovery path instead.
- Do not treat a health check that runs successfully as a reason to send a notification. Success is the default, not an event.
