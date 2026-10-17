# OpenViking Agent Experience / `experiences` memory type — known extraction bug

> Found 2026-10-17 while diagnosing "还没有 Agent 经验" (no Agent Experience entries) in OpenViking Studio.

## Symptom

The **Agent 经验** (Agent Experience) page in OpenViking Studio shows "还没有 Agent 经验" even after many session commits. Other memory types (`entities`, `events`, `preferences`, `patterns`) extract normally.

## Root cause — OpenViking Issue #5599 (open, unfixed as of v0.4.23)

`openviking/session/memory/session_extract_context_provider.py` (~line 498–503) has a hardcoded filter:

python
schemas = [
    s for s in self._get_registry().list_all(include_disabled=False)
    if getattr(s, "stage", "user") == "user"   # ← only stage=user types pass
]


The `experiences` memory type is defined with `stage: agent` + `agent_only: true`, so it is **always dropped** by this filter — regardless of `agent_evolution.enabled` in `ov.conf`.

### Evidence chain

1. Schema-list probe (temporary log at the filter): assembled schemas are `['profile', 'identity', 'cases', 'events', 'preferences', 'soul', 'experiences', 'entities', 'trajectories']` — but only **after** patching the filter to `in ("user", "agent")`. Before the patch, `experiences` is absent.
2. With the patch applied, `SchemaModelGenerator` builds the flat data model **including** `experiences` (fields: `page_id` / `experience_name` / `content` / `supersedes`).
3. Even with the schema present, the VLM emits **0 experiences operations** across ~150 varied commits — the model consistently prefers `entities`/`events`/`preferences` and skips the most demanding op type.
4. A separate but related issue: the `experiences` pipeline has a hard dependency on `cases` ops that the model never produces (`if agent_evolution_enabled and cases_allowed and _TRAJECTORIES_MEMORY_TYPE in agent_memory_types:` → `train_from_extracted_cases(...)`).

## Workaround that works

Standalone distillation — read a completed session's archives, make one VLM call with the experiences template rules, write the resulting cards via `POST /api/v1/content/write` into `memories/experiences/`.

The issue reporter used this to produce **313 cards from 162 technical sessions**.

### Steps

1. Commit the session: `POST /api/v1/sessions/{session_id}/commit`
2. Read the archive: `GET /api/v1/content/read?uri=viking://user/default/sessions/{session_id}/history/archive_001`
3. Make a VLM call with the experiences extraction template (see OpenViking source for the template rules)
4. Write results: `POST /api/v1/content/write` with target `viking://user/default/memories/experiences/`

## What `agent_evolution.enabled` does NOT do

Setting `agent_evolution: {enabled: true}` in `ov.conf` does **not** fix this. The filter is unconditional — it runs before any `agent_evolution` check. The config flag is currently a no-op for `experiences` extraction.

## What DOES work normally

These memory types extract fine from session commits (they are `stage: user`):

| Memory type | Status |
|---|---|
| `entities` | ✅ Extracts |
| `events` | ✅ Extracts |
| `preferences` | ✅ Extracts |
| `patterns` | ✅ Extracts |
| `identity` | ✅ Extracts |
| `profile` | ✅ Extracts |
| `soul` | ✅ Extracts |
| `experiences` | ❌ Never extracted (bug) |
| `trajectories` | ❌ Never extracted (same filter) |

## When to care vs. when to ignore

- **Ignore** if you only need cross-session memory for the agent — `entities`, `events`, and `preferences` cover the core use case.
- **Investigate** if you specifically want the Agent Experience page in Studio to populate, or if you're building on the `experiences`/`trajectories` memory types for agent self-evolution workflows.

## Related

- OpenViking GitHub: https://github.com/volcengine/OpenViking/issues/5599
- OpenViking config docs: https://github.com/volcengine/OpenViking/blob/main/docs/en/guides/01-configuration.md
- PR #5629 (linked to the issue, may contain a fix)
