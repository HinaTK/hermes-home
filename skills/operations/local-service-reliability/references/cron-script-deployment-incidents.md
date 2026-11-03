# Cron Script Deployment Incidents (Hermes Desktop, Windows)

Incident log + acceptance protocol for cron-registered Python scripts. Companion to the SKILL.md section "Cron-session interpreter identity (Desktop)".

## Root cause

In cron sessions spawned by the Hermes scheduler, `sys.executable` is the Hermes CLI binary. Child processes launched via `sys.executable` fail with `usage: hermes [-h] [--version] [-z PROMPT] ...` because argparse treats the child script path as a CLI argument. Five variants of this class occurred (2026-10 through 2026-10-29): direct `sys.executable` child spawn in a wrapper, plus related script-field misuse.

## Verified fix pattern (blueprint: `scripts/grid_weixin_execute.py`, `scripts/rate_ignition_monitor_wrapper.py` in hermes-home)

```python
import os, subprocess, sys

SYSTEM_PY = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
_IS_312 = sys.version_info[:2] == (3, 12) and 'Programs' in sys.executable

if __name__ == '__main__' and not _IS_312:
    sys.stdout.flush(); sys.stderr.flush()
    sys.exit(subprocess.call([SYSTEM_PY, os.path.abspath(__file__)] + sys.argv[1:]))
```

All child invocations then use `[SYSTEM_PY, target, ...]` explicitly. Flush stdout/stderr before re-exec so partial output is not lost.

## Deployment acceptance protocol (order matters)

1. Run the script locally with the pinned interpreter → expect exit 0.
2. Run the wrapper end-to-end → expect exit 0.
3. `cronjob action=run` (real scheduler session) → read the delegation result and/or `last_status` from `cronjob list`.
4. A watchdog/silent-mode script "completed, empty output" is a PASS, not a failure — silence is the designed behavior when no alert conditions hold.

## Stale-notification diagnosis (2026-10-29 incident)

Timeline that fooled nobody once checked: 15:40 scheduled run failed (pre-fix wrapper) → 16:02 fix committed → 16:01 and 16:21 real cron runs `ok`/silent. The user's forwarded error was the 15:40 notification. Verdict came from `cronjob list` timestamps + `git log` of the script — not from re-debugging the error text.

## Related class: git push protection after secret purge

Nightly git-push cron jobs fail with `GH013: Repository rule violations found (Push cannot contain secrets)` when secret-bearing commits are still ancestors of the pushed branch. After a history purge (soft-reset / rebase), verify BEFORE trusting the next nightly run:

```bash
git merge-base --is-ancestor <secret-commit-sha> main && echo "still in history" || echo "purged"
git fetch origin -q && git rev-list origin/main..main --count   # expect 0 when synced
git push --dry-run origin main                                  # "Everything up-to-date" = clear
```

The push-protection block URL can be used to unblock a specific secret, but purging the commit from branch history is the durable fix. Also keep a pre-commit secret guard in the push script itself so new commits never re-introduce keys.

## 2026-11-03: relay `print()` newline doubling broke Feishu tables

Symptom: user replied "这都不是表格" to the watchtower (观察哨) cron push — the markdown table rendered as broken prose.

Chain (byte-verified against `cron/output/0740a34e4711/2026-11-03_15-51-*.md`):
1. Child monitor prints in Windows text mode → `\r\n` per line.
2. Wrapper does `print(r.stdout.decode(...))` → wrapper's own text-mode stdout translates the `\n` again → pipe carries `\r\r\n`.
3. Hermes reads with universal newlines → two newlines per line → every line separated by a blank line.
4. Blank line between `| 哨 | 状态 | 读数 |` and `| --- |` → Feishu does not recognize a table.

Why the first grep found nothing: the archived .md normalizes to CRLF, so `b"\r\r"` appears 0 times across ALL cron outputs. The surviving scar is a blank line between every pair of adjacent table rows. Audit via row-index gaps (`[i for i,l in enumerate(lines) if l.strip().startswith('|')]`, adjacent gaps must be 1). That audit showed: watchtower 3/3 pushes broken, rate_ignition wrapper carried the same latent pattern, direct-print jobs (market_phase_monitor) clean. Blank lines between a table and a following heading are normal markdown — only gaps INSIDE one table block are the defect.

Fix (hermes-home d664cbe): both wrappers extracted `relay(raw)` — decode, normalize `\r\n`/`\r` → `\n`, write via `sys.stdout.buffer`. TDD: `scripts/test_cron_relay_newline.py` RED on missing `relay`, GREEN after; full scripts suite 43 tests pass; end-to-end acceptance ran the real wrapper under `subprocess.run(..., capture_output=True)` and byte-checked the table (6 rows, all gaps == 1).

Also found during TDD: `watchtower_wrapper.py` ran its monitor at import time (module-level code outside `__main__`) — importing it in a test executed the entire live pipeline.

Companion bug in the same push (different repo, AH_analyse 6fb8828): the "🔔A级命中" alert itself was a false positive — "该工具创设以来的第三次操作" ("since the tool's creation") matched the keyword 创设. Keyword-tier grading must strip historical-reference phrases before matching; see the market-phase-monitoring skill for watchtower grading rules.
