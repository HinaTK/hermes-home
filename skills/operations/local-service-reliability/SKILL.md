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

## What not to do

- Do not equate `available`, `running`, or `healthy` with end-to-end readiness.
- Do not re-use a stale watch-pattern alert as proof of a current failure.
- Do not run two independent supervisors for the same process.
- Do not repair by deleting vector data, resetting credentials, or reinstalling runtimes before preserving evidence.
- Do not capture a transient setup failure as a permanent tool limitation; record the working recovery path instead.
