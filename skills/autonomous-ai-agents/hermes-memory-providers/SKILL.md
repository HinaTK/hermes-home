---
name: hermes-memory-providers
description: "Use when configuring Hermes external memory providers."
version: 1.0.0
---

# Hermes external memory providers

Configure Hermes Desktop/CLI to use one external memory provider (OpenViking, Honcho, Mem0, …) **additively** with built-in MEMORY.md / USER.md. Only one external provider can be active.

Official docs: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers
OpenViking + Hermes: https://docs.openviking.ai/en/agent-integrations/05-hermes

Machine-specific paths and the verified local OpenViking layout live in `references/openviking-desktop.md`.

### Known issue: `experiences` memory type never extracts

OpenViking v0.4.21–v0.4.23 has a hardcoded filter that drops `stage: agent` schemas (including `experiences` and `trajectories`) during session-commit extraction. The Agent Experience page in Studio will show "还没有 Agent 经验" regardless of `agent_evolution.enabled`. See `references/openviking-experiences-bug.md` for root cause, workaround, and when to care.

## Hard rules

- Keep the **OpenViking (or other provider) Python env separate** from Hermes. Hermes talks HTTP; do not `pip install openviking` into the Hermes runtime / Desktop `_internal` venv. Do not `--force-reinstall` OpenViking on top of Hermes.
- Resolve Hermes home from `$HERMES_HOME` (Desktop managed profile is not `~/.hermes`). Use that profile's `config.yaml` and `.env`.
- Settings go in `config.yaml` via `hermes config set`; secrets/connection env vars go in the active profile `.env`. Never put non-credential settings in `.env` except the provider's documented `OPENVIKING_*` / equivalent keys.
- Do not hand-edit `config.yaml` (indent/BOM can break the live gateway). Prefer `hermes config set KEY VAL`.
- `hermes memory setup <provider>` is interactive. When driving setup from an agent session, configure non-interactively: write `ov.conf` / `ovcli.conf` (or provider JSON), set `memory.provider`, write env keys, then `hermes memory status`.
- New `viking_*` (or provider) tools load only on a **new session** / `/reset`. Tell the user that; do not claim they work in the current turn.

## Locate the CLI on Desktop

`hermes` is often missing from PATH. Use the Desktop launcher:

```text
$HERMES_HOME/../desktop-bin/hermes.cmd   # typical: <Desktop>/data/desktop-bin/hermes.cmd
```

Then:

```bat
hermes.cmd memory status
hermes.cmd memory setup openviking
hermes.cmd config set memory.provider openviking
hermes.cmd config get memory
```

## OpenViking (self-hosted) workflow

1. Install OpenViking into its **own** venv (`uv venv` + `uv pip install openviking`). uv venvs on Windows may lack pip — use `uv pip install --python <venv>/Scripts/python.exe`.
2. Write `~/.openviking/ov.conf` (server: storage, embedding, vlm, host/port) and `ovcli.conf` (client: url, optional api_key).
3. Validate **without** starting the HTTP server: `python -m openviking_cli.doctor` with `OPENVIKING_CONFIG_FILE` set. Prefer this over `openviking-server --version` / `--help` (those can hang while loading RAGFS).
4. Start the server from that venv (`openviking-server --host 127.0.0.1 --port 1933`). Local bind + no `root_api_key` = `dev` auth.
5. Point Hermes at it: `memory.provider=openviking` plus `.env` `OPENVIKING_ENDPOINT=http://127.0.0.1:1933` (and ACCOUNT/USER for local trusted mode). Leave `OPENVIKING_API_KEY` empty for local dev.
6. Verify: `GET /health` then `hermes memory status` → Provider openviking, Status available. Smoke write: `POST /api/v1/content/write`.
7. If Hermes should auto-start a missing local server, `openviking-server` must be on PATH (`shutil.which`). A tiny wrapper that sets `OPENVIKING_CONFIG_FILE` and execs the venv binary is enough; do not copy the server into the Hermes env.

### Windows restart and verification pitfall

A restart command can remain alive while OpenViking is still initializing, so an immediate health probe may report `connection refused` even though startup will succeed moments later. Treat this as a readiness race first: start the known-good wrapper, wait for its log line `OpenViking HTTP Server is running on 127.0.0.1:1933` (or poll `/health` with a bounded timeout), then verify `/health` and `/api/v1/system/status`. Only after those probes pass should Hermes be checked with `hermes.cmd memory status`. On this Desktop layout, invoke the wrapper with `cmd.exe /c "C:\\Users\\Administrator\\.openviking\\start-openviking.cmd"`; it sets `OPENVIKING_CONFIG_FILE` and launches the OpenViking venv executable without contaminating Hermes's Python environment.

The OpenViking doctor must be run with the OpenViking venv interpreter, not the system Python. An empty successful stdout is not evidence of an all-pass report; use the HTTP health/system probes as the authoritative runtime check and report doctor output accurately.

## Embedding / VLM on Windows without a C compiler

Local GGUF embedding (`provider: local`, default `bge-small-zh-v1.5-f16`) needs `llama-cpp-python`. Source builds hang if cmake/MSVC are missing. Install **CPU wheels** instead:

```bat
uv pip install --python <venv-python> llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

Do not wait on `openviking[local-embed]` compiling from sdist. VLM can be any OpenAI-compatible chat/vision model (`provider: openai`, `api_base` ending in `/v1`). Chat-only gateways often have **no** `/embeddings` route — do not assume the Hermes chat key can serve dense embeddings.

## Verify before declaring done

- `hermes memory status` shows the intended provider as active and available.
- OpenViking `/health` returns healthy (or the remote/cloud equivalent).
- Doctor all-pass for a new local install.
- User told to start a **new chat** so provider tools attach.
