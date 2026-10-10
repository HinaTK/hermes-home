# OpenViking on Hermes Desktop (this machine)

Verified 2026-09-21 against Hermes Desktop 0.21.0-cn.18 + OpenViking 0.4.21.

## Layout

| Piece | Path |
|---|---|
| Hermes home | `D:\\Hermes Agent CN Desktop\\data\\hermes-home` (`$HERMES_HOME`) |
| Hermes CLI | `D:\\Hermes Agent CN Desktop\\data\\desktop-bin\\hermes.cmd` |
| OpenViking venv | `C:\\Users\\Administrator\\.openviking\\venv` |
| Server config | `C:\\Users\\Administrator\\.openviking\\ov.conf` |
| Client config | `C:\\Users\\Administrator\\.openviking\\ovcli.conf` |
| Workspace | `C:\\Users\\Administrator\\.openviking\\data` |
| Restart script | `C:\\Users\\Administrator\\.openviking\\start-openviking.cmd` |
| PATH wrappers | `C:\\Users\\Administrator\\bin\\openviking-server` and `.cmd` |

Endpoint: `http://127.0.0.1:1933` (dev auth, no API key).

## Hermes connection

`memory.provider: openviking`

`.env` keys (no API key for local dev):

```text
OPENVIKING_ENDPOINT=http://127.0.0.1:1933
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=default
```

Optional YAML (saved via `hermes config set`; plugin also reads `.env`):
`memory.openviking.endpoint/account/user`.

## ov.conf shape that passed doctor

- storage: local workspace + local vectordb/agfs
- embedding.dense: `provider=local`, `model=bge-small-zh-v1.5-f16`, `dimension=512`
- vlm: OpenAI-compatible `glm-4.6v` at `https://aicode-api.gz4399.com/api/v1` (chat key; that gateway has no `/embeddings`)
- server: `127.0.0.1:1933`

Doctor: `OPENVIKING_CONFIG_FILE=... python -m openviking_cli.doctor` (stdout from `openviking-server doctor` may be empty if imported as a module-less exe hang; calling `openviking_cli.doctor.main()` printed checks).

## llama-cpp-python

Installed from `https://abetlen.github.io/llama-cpp-python/whl/cpu` into the OpenViking venv. Default PyPI sdist build is the wrong path here (no MSVC/cmake).

## Checks that succeeded

- `GET /health` → `status=ok`, `version=0.4.21`, `auth_mode=dev`
- `GET /api/v1/system/status` → `user=default`
- `POST /api/v1/content/write` create under `viking://user/default/memories/...`
- `hermes.cmd memory status` → Provider openviking, Status available
