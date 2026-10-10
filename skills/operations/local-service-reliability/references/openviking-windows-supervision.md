# OpenViking + Hermes Desktop: validated Windows pattern

## Observed failure classes

1. **Server absent**: `127.0.0.1:1933` refuses connections. Hermes may log that `openviking-server` is not on PATH. Start the known-good wrapper with its explicit config, then wait for the readiness line or poll `/health`.
2. **Server healthy but semantic search broken**: `/health` and `/api/v1/system/status` return success, but search fails in `intent_analyzer` when the configured VLM model is unsupported upstream. This was observed with `glm-4.6v`, which returned HTTP 404 `model_not_found`.
3. **Stale alert**: an old background process can continue to expose a prior traceback after a newer process has been restarted successfully. Inspect process IDs and timestamps.

## Validated recovery sequence

1. Back up `C:\Users\Administrator\.openviking\ov.conf` outside the active data path.
2. Query the configured OpenAI-compatible provider's live model endpoint without printing the API key.
3. Send a minimal non-streaming completion using a model confirmed to return HTTP 200.
4. Update both `ov.conf` and the local config generator if one exists.
5. Restart the OpenViking server from its dedicated venv.
6. Verify `/health` and `/api/v1/system/status`.
7. Run a real Viking semantic search through Hermes tools; do not stop at HTTP checks.

In the incident that produced this reference, `glm-5.3-flash` returned HTTP 200 for a minimal completion and subsequent Viking semantic search returned the expected stored memories.

## Supervision pattern

Use one Windows Scheduled Task named `OpenViking_Supervisor` at user logon with a short delay. It runs a dedicated supervisor from the OpenViking home directory. The supervisor:

- polls `/health` at a bounded interval;
- starts the dedicated `openviking-server.exe` only when the endpoint is unhealthy and no child is already running;
- sets `OPENVIKING_CONFIG_FILE` and `OPENVIKING_CLI_CONFIG_FILE` explicitly;
- waits up to a bounded readiness timeout;
- logs start and readiness results under `.openviking/logs/`.

Use task settings that allow running on battery, do not stop on idle, ignore duplicate instances, start when available, and restart the supervisor after failure. Read the task XML/status back after creation and run it once. A task can exist but still be invalid if its last result is nonzero or the supervisor exits immediately.

## Readiness acceptance criteria

- only one OpenViking server owns port 1933;
- supervisor task is enabled and has the intended command, working directory, trigger, and restart settings;
- `/health` is healthy;
- `/api/v1/system/status` is initialized;
- Hermes memory provider reports available;
- a real semantic search returns stored memories;
- current supervisor log has no new traceback or model error.
