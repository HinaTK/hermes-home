# Full research reruns: acceptance and reporting

## Execution is not completion

A manually triggered cron returning a background handle means started, not completed. Wait for its completion notification without repeatedly polling a cron task. If it fails, read the complete saved traceback rather than the truncated chat alert. Identify the failed boundary before retrying.

An import-only or --help smoke test verifies launchability, not a complete research run. A successful ordinary-Python launch does not prove the scheduled host uses that interpreter or shares its module environment. Verify the actual production entry separately; do not report an unresolved launcher repair as complete because a direct research run succeeded.

When a tested standalone interpreter can execute the existing research module, direct execution of that same full CLI is a valid recovery path. Preserve the default pool, windows, latest closed-session resolution and state gates; disclose that direct execution does not itself deliver a Feishu message. Do not silently substitute offline caches, a sample pool, or historical asof to obtain a green status.

## Read the exact run artifacts

After exit, inspect that run's summary, report and error records. Report:
- actual common window and cutoff;
- attempted assets, successful/failed window runs, and complete four-window assets;
- data failure versus legitimate model exclusion where available;
- all live holdings, with simulated net spread clearly separated from actual fills and inventory P&L;
- whether production continuity/priority state was eligible to advance;
- report path and separately verified delivery status.

Exit code zero means the pipeline completed, not that coverage is complete. Degraded coverage must remain explicit and must not be presented as a clean rotation trigger.

## Empty sections and ranking semantics

A rotation shortlist can be empty because no candidate beats its baseline. State this explicitly rather than leaving a bare heading, fabricating ten rows, or replacing it with the complementary score ranking. A universe-by-cycles top ten is a separate, explicitly labeled view, computed from saved complete-coverage rows. Preserve the distinction between a rendering defect, a legitimate empty filtered set, and missing result data; investigate before naming the cause.

## Why the module exists: the hand-rerank bypass failure (2026-10-20/23)

The user twice received "top 10" tables built by hand-reordering `result.json` in chat, while `tools/etf_research/entry_rank.py` — which applies the entry-eligibility gate — sat committed in the repo since 10-21 (`10d479d`) unused. Root cause: the answering path defaulted to "read the file, sort, deliver" without ever checking whether a module for that exact deliverable existed. Rule: before any ranking/summary deliverable, list the relevant `tools/` directory for an existing entrypoint; if one exists, run it — hand-assembly in the chat layer is a process failure even when its arithmetic is right. (User asked "所以为什么绕过了脚本？" — the answer "no good reason, I never looked" had to be admitted explicitly.) Also distinguish runs carefully when reporting: same-day multiple research runs exist (e.g. 2026-10-23 had both `...-152537` hand-reranked and `...-170032` module-run); name which run a table came from.

## Evidence limits

Do not infer today's true turnover from an old 104-session backtest, or compare it directly with a new 63-session run. Read current model parameters before asserting they match the user's live 1.5% grid and lot budgets. Simulation net spread excludes unclosed inventory effects unless explicitly modeled and reported.
