# Recall channels — verified on this Desktop (2026-11-02)

Live evidence for the four-channel model in SKILL.md. Verified with real tool output, not docs alone.

## Built-in memory on this machine

- Files: `$HERMES_HOME/memories/MEMORY.md` and `USER.md` (plus `.lock` siblings) under `D:\Hermes Agent CN Desktop\data\hermes-home\memories\`.
- Char limits are user-customized in config.yaml: `memory.memory_char_limit: 5200`, `memory.user_char_limit: 3375`. Defaults are 2,200 / 1,375 — do not "correct" them back.
- Injection format observed in the system prompt: header `MEMORY (your personal notes) [97% — 5,088/5,200 chars]`, entries separated by `§`.
- Frozen snapshot: entries written mid-session hit disk immediately but enter the system prompt only at the NEXT session start (prefix-cache preservation).

## Channel 2: per-turn prefetch — observed

A user turn about "can a new session recall a past pitfall" arrived with a `<memory-context>` block already attached, containing three recalled memories with full `viking://` URIs (10-13 plan A selection, 10-31 ledger-copy instruction, 09-30 rolling-window alert fix), each with Summary + raw ChatLog excerpts. No agent action needed — prefetch fired before the turn reached the model.

## Channel 3: viking_search — observed

Query about user-correction events (被用户纠正的错误 / 算错账 / 教训) returned scored hits across types, e.g. `events/2026/10/14/自动建议旧账本报错.md` (score 0.528) — a past pitfall ("delivery incomplete, still reading old ledger") recalled intact with the original admission. Correction events DO extract on v0.4.21 because they land as `events`, not `experiences`.

## Channel 4: session_search — observed

FTS5 found the original 10-27 conversation where the user corrected a reversed bank-sector narrative, including the assistant's on-the-spot admission. Keyword-literal: needs the actual words (e.g. `卖E接F`, `纠正`), not paraphrase.

## Failure modes to disclose when answering recall questions

1. Semantic mismatch: prefetch will not surface an unrelated-domain pitfall (ledger bug during a Nasdaq chat) unless the agent proactively searches.
2. `experiences` type never extracts (see `references/openviking-experiences-bug.md`); pure "lesson" memories may be lost — correction events survive as `events`.
3. No commit, no extraction: long-running gateway sessions may not hit session-commit for weeks.
4. MEMORY.md is capacity-bound (5,200 chars here, typically ~95% full): iron rules displace each other; consolidate before adding.

## Answer pattern that worked

When the user asks "can a new session recall X": give the four-channel table, then DEMONSTRATE — run one `viking_search` and one `session_search` live on their example and show the hits. Demonstrated recall beats mechanism description, and it doubles as a provider health check.

## CLI invocation from git-bash (MSYS)

`cmd.exe /c "D:\Hermes Agent CN Desktop\data\desktop-bin\hermes.cmd" memory status` fails — the quoted spaced path gets mangled (GBK `不是内部或外部命令`). Working form:

```bash
cd "D:/Hermes Agent CN Desktop/data/desktop-bin" && cmd.exe /c hermes.cmd memory status
```

`hermes memory status` on this machine confirms: built-in injection / profile / tool all enabled, provider openviking, plugin installed, status available.
