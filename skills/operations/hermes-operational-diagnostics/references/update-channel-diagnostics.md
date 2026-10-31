# "How out of date is Hermes?" — three independent update channels

Verified 2026-10-31 on the managed Windows desktop install. The question looks trivial and is
routinely answered wrong, because this machine runs **two independent Hermes installations** with
**separate updaters**, and the one-command answer points at the wrong one.

## The trap

`hermes --version` on the PATH binary printed:

```
Hermes Agent v0.22.1+72.g450ad50 (2026.9.24) · stable · local 450ad5055eb3
Install directory: C:\Users\Administrator\AppData\Local\hermes\hermes-agent
Install method: git
Update available — run 'hermes update'
```

That "Update available" describes the **C: CLI git checkout only**. The user was chatting inside the
**D: managed desktop app**, which has its own hot-update channel and was *not* behind. Answering
"you're 16 days behind" without naming which installation is a false alarm.

## Channel 1 — Desktop shell + CN runtime (what the user actually sees)

Root: `D:\Hermes Agent CN Desktop\`. All state under `data/`.

| File | What it proves |
|---|---|
| `data/current.json` | Installed runtime: `runtimeVersion`, `kernelVersion`, `installedAt`, `sourceRepo`, `sourceCommit`, `artifactSha256` |
| `data/update-config.json` | Which updater endpoints are live: `releaseManifestUrl`, `runtimeBaseUrl`, `shellUpdaterEndpoint`, `channel` |
| `data/software-update.json` | Last check result: `checkedAt` (epoch ms), `currentVersion`, `phase`, `error`, `warnings` |
| `data/versions/<ver>/manifest.json` | Per-artifact `artifactUrl` + version, useful to see the mirror layout |

The stable version actually published is one curl away — do not infer it from the app:

```bash
curl -s https://desktop.hermesagent.org.cn/latest.json | head -c 2000
# -> {"repository":"Eynzof/Hermes-CN-Desktop","version":"v0.9.0","publishedAt":"2026-09-21T03:42:07Z", ...}
```

`.../runtime/latest.json` and `.../runtime/0.21.0-cn.18.json` return 404 `Unknown component update` —
runtime versions are announced through the shell's own manifest, not a per-runtime latest file.
`https://hot-update.hermesagent.org.cn/v1/check/...` returns `{"error":"unauthorized"}` to curl
(it wants the app's device signature); that is **not** evidence the updater is broken.

Upstream for this channel is the CN fork, not NousResearch:

- `Eynzof/Hermes-CN-Core` — the kernel/runtime (tags `runtime-v0.21.0-cn.18`, …)
- `Eynzof/Hermes-CN-Desktop` — the Electron shell (tags `v0.9.0`, `v0.9.1-prototype.nightly.*`)

Activity check when the GitHub API is rate-limited (it returns
`API rate limit exceeded for <ip>` and no data — treat that as *no data*, never as "no releases"):

```bash
curl -s https://github.com/Eynzof/Hermes-CN-Core/commits/main.atom | grep -E '<updated>|<title>' | head -20
curl -s https://github.com/Eynzof/Hermes-CN-Desktop/commits/main.atom | grep '<updated>' | head -6
```

Verified state 2026-10-31: CN-Core last commit 10-15, CN-Desktop last commit 09-21, stable release
v0.9.0 published 09-21. So the desktop was **current but the fork itself had gone quiet ~16/40 days** —
those are different findings and both matter to the user.

## Channel 2 — CLI git install (independent, NousResearch upstream)

`C:\Users\Administrator\AppData\Local\hermes\hermes-agent`, remote
`https://github.com/NousResearch/hermes-agent.git`. Measure lag like this, in this order:

```bash
cd "C:/Users/Administrator/AppData/Local/hermes/hermes-agent"
git fetch origin main                       # WITHOUT this the lag reads 0 — origin/main is stale
 git rev-list --count HEAD..origin/main     # 6351
git merge-base --is-ancestor HEAD origin/main && echo ancestor || echo forked
git log -5 origin/main --format='%h | A:%ad | C:%cd | %s' --date=format-local:'%Y-%m-%d %H:%M'
git status --porcelain                      # dirty tree can block the updater
git log HEAD..origin/main --format='%s' | sed -E 's/^([a-z]+)(\([^)]*\))?:.*/\1/' | sort | uniq -c | sort -rn | head -15
```

Two measurement bugs bite here:

1. **Un-fetched remote.** `git rev-list --count HEAD..origin/main` returned `0` before the fetch and
   `6351` after. Always fetch first, and say so when reporting.
2. **Committer date lies.** A rebase/merge rewrite stamps `%cd` with the push time. The 5 newest
   upstream commits were *authored* 10-29/10-30 but *committed* 2026-10-31 17:03, which naively reads
   as "0.02 days old / updated half an hour ago". Use `%ad` (author date) for "how fresh is this
   project", and mention committer date only when you are explicitly talking about a push event.

Commit-type histogram over `HEAD..origin/main` is the cheapest honest way to say what you're missing
(verified: 3217 fix, 837 chore, 593 test, 389 feat, 296 refactor).

## Channel 3 — bundled/portable runtimes

`data/versions/<ver>/` may hold several runtimes; `data/current.json` names the active one. Never
report the directory mtime of a version folder as "last updated" — it changes on unrelated internal
rewrites (a `_internal/` or `node/` touch moved one folder's mtime to 10-31 while the binary inside
was still 09-21).

## Reporting contract

Lead with a two-row table naming the installations (`desktop` vs `CLI`), then say separately:

- is the *installed* version the latest published one? (channel 1 manifest)
- is the *project* still shipping? (fork commit activity)
- how far behind is the *other* installation? (channel 2 fetch + author date)

Never merge those three into one "up to date / out of date" verdict, and never let a CLI
`Update available` line stand in for the desktop's update state.
