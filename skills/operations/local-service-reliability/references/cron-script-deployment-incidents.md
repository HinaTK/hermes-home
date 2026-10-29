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
