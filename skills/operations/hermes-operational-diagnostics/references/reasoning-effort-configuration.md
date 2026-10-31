# Reasoning / thinking effort — configuration, ladder, and verification

Verified 2026-10-31 against the managed desktop install at
`D:\Hermes Agent CN Desktop\data\hermes-home` (source checkout at
`C:/Users/Administrator/AppData/Local/hermes/hermes-agent`).

## What the user is asking for

"把默认思考程度改成最高" / "set thinking to max" means: change the **global default**
`agent.reasoning_effort` in `$HERMES_HOME/config.yaml`. It does not mean the current
session, and it does not mean a per-model alias override.

## The command, and the misleading warning

```bash
export HERMES_HOME="D:/Hermes Agent CN Desktop/data/hermes-home"   # managed desktop home
hermes config set agent.reasoning_effort max
```

Output observed:

```
✓ Set agent.reasoning_effort = max in D:\Hermes Agent CN Desktop\data\hermes-home\config.yaml
⚠ 'agent.reasoning_effort' is not a recognized config key — it was saved anyway, but Hermes may not read it.
  Did you mean: agent.reasoning_echo
  (Use --force to skip this notice.)
```

The warning is **wrong**. Evidence:

- `hermes_constants.py:1178` — `effort = agent_cfg.get("reasoning_effort", "")` inside
  `resolve_reasoning_config()`, whose docstring calls itself the "single chokepoint for
  every surface (CLI, gateway, TUI, cron, `/model`, fallback activation)".
- `agent/chat_completion_helpers.py:2038` and `agent/agent_runtime_helpers.py:2502`
  both re-resolve through it.

So: keep the CLI write (do not hand-edit config.yaml), and simply tell the user the
warning is a stale key-table artifact. Do **not** "fix" it by inventing a different
key such as `agent.reasoning_echo`.

## The ladder

`agent/reasoning_effort.py`:

```
EFFORT_LADDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")
```

`VALID_REASONING_EFFORTS` in `hermes_constants.py` is the same list minus `none`;
`none`/`false`/`disabled` mean *disabled* (`{'enabled': False}`), not a low level.

**`ultra` is Hermes-internal — the Codex product tier. No wire accepts it; every
declared per-provider set stops at `max`.** `clamp_effort()` therefore maps `ultra` →
`max`. When the user asks for "the highest", answer with `max` and explain why — do not
write `ultra` and let it be silently clamped.

### Per-provider ceilings (same file)

| Wire family | Accepted levels |
|---|---|
| `OPENAI_COMPAT_WIRE_EFFORTS` (OpenRouter, Nous Portal, generic `custom`) | none, minimal, low, medium, high, xhigh, max |
| `CODEX_GPT56_EFFORTS` / `CODEX_LEGACY_EFFORTS` | none, low, medium, high, xhigh[, max for 5.6/6-tier] |
| `GLM52_EFFORTS` | high, max (`xhigh`→max) |
| `GLM53_EFFORTS` | low, medium, high, max (`xhigh`→max) |
| `KIMI_K3_EFFORTS` | low, high, max (`medium`→high, `xhigh`→max) |
| `XAI_GROK46_EFFORTS` | low, medium, high, xhigh |
| `GEMINI4_THINKING_LEVELS` | low, medium, high (cannot disable) |

Clamping goes to the nearest **weaker** level when the exact one is unsupported — so an
over-request degrades silently. If quality looks unchanged after raising the level, the
suspect is the downstream route, not the config write.

## Verification (do this, don't trust the file)

```python
import yaml
from hermes_constants import resolve_reasoning_config

cfg = yaml.safe_load(open(r"D:/Hermes Agent CN Desktop/data/hermes-home/config.yaml", encoding="utf-8"))
print(cfg["model"]["default"], cfg["model"]["provider"])
print(cfg["agent"].get("reasoning_overrides"))     # per-model map WINS over global
print(resolve_reasoning_config(cfg, cfg["model"]["default"]))
print(resolve_reasoning_config(cfg, ""))
```

Run with `PYTHONPATH=<hermes-agent checkout>` from that checkout. Observed result:

```
model.default = group/smart-split
model.provider = custom:127-0-0-1-3425
reasoning_overrides = None
'group/smart-split' -> {'enabled': True, 'effort': 'max'}
''                  -> {'enabled': True, 'effort': 'max'}
```

A non-empty `agent.reasoning_overrides` containing the active model's slug will beat the
global value — always print it before declaring the change effective.

## Scope boundary to state in the reply

`reasoning_config` is resolved at session init and re-resolved on model switch, so the
conversation that asked for the change **keeps its old effort**. Tell the user to open a
new session (`/new`) or re-select the model to pick up `max`. Reporting "now running at
max" for the current chat is false.

## Aggregator / relay caveat

When the active provider is a local relay (e.g. `custom:127-0-0-1-3425` with
`group/smart-split`), `max` is only what Hermes *requests*. Whether the relay's backend
model honours it is outside Hermes. Mention this as a possible explanation if latency
rises without quality gains — and note that the per-model escape hatch is
`agent.reasoning_overrides.<model>` rather than lowering the global default.
