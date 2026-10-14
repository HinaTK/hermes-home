# Hermes Gateway Lifecycle — Windows Desktop Evidence

## Key log files and their locations

| File | Path | Purpose |
|---|---|---|
| Gateway lifecycle ledger | `HERMES_HOME/logs/gateway-exit-diag.log` | JSON lines: `gateway.start`, `gateway.previous_unclean_exit` |
| Desktop restart log | `HERMES_HOME/logs/desktop-gateway-restart.log` | Full restart log with preflight summary |
| Gateway runtime log | `HERMES_HOME/logs/gateway.log` | Platform connections, inbound/outbound events |
| Start timestamps | `HERMES_HOME/gateway-starts.log` | Unix epoch timestamps of each gateway start (root, NOT `logs/`) |
| Errors log | `HERMES_HOME/logs/errors.log` | Python tracebacks, exceptions |
| Agent log | `HERMES_HOME/logs/agent.log` | Agent-level activity |

## Validated restart sequence (2026-10-14)

When the desktop UI restart is unavailable or the gateway remains stopped:

1. **Confirm stopped:** `ps aux | grep hermes` returns nothing; `gateway.log` tail shows no active control pipe.
2. **Launch with `--replace`:**
   
   "D:\\Hermes Agent CN Desktop\\data\\versions\\0.21.0-cn.18\\hermes-agent-cn-runtime-win32-x64.exe" gateway run --replace

3. **Verify startup in `logs/gateway.log`:**
   
   Connecting to feishu...
   Connecting to weixin...
   [Feishu] Connected in websocket mode (feishu)
   ✓ feishu connected
   ✓ weixin connected
   Gateway running with 2 platform(s)

4. **Confirm new start timestamp** in `gateway-starts.log` (root of `HERMES_HOME`).

## Periodic unclean exit pattern

Observed on Windows desktop: gateway dies at irregular 2–6 day intervals. Every entry in `gateway-exit-diag.log` shows:


{"tag": "gateway.previous_unclean_exit", "state_db_integrity": "ok", "suspected_oom": false}


**Classification:** External kill (SIGKILL / VM death / Windows-level termination), NOT a Hermes crash. No traceback in `errors.log` between `last_heartbeat_at` and restart.

**Do not:** open a bug report, rotate credentials, or treat this as a code defect. The state is clean.

**Do:** recommend Windows Event Viewer check or `.vbs` wrapper for service-style supervision.

## Service-style launch wrappers

Located at `HERMES_HOME/gateway-service/`:

- `Hermes_Gateway.cmd` — batch file setting all required env vars and invoking the runtime
- `Hermes_Gateway.vbs` — VBScript wrapper for more resilient background execution

Both invoke the same runtime with `HERMES_HOME`, `PYTHONIOENCODING=utf-8`, `HERMES_GATEWAY_DETACHED=1`, `HERMES_SUPERVISED_CHILD=1`, `VIRTUAL_ENV`, and `PYTHONPATH` set.
