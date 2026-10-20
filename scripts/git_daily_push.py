#!/usr/bin/env python3
"""每日 23:00 自动检查 git 状态并推送（支持多仓库）。

流程（每个仓库独立执行）：
  1. git fetch origin — 拉取远端最新
  2. git status --porcelain — 检查本地是否有未提交变更
  3. 有变更 → git add -A && git commit -m "[auto] daily push <date>"
  4. 落后远端 → git pull --rebase origin <branch>
  5. git push origin <branch> — 推送到远端
  6. 输出简洁结果摘要
"""

import subprocess
import sys
import os
from datetime import date

# (仓库路径, 分支)
REPOS = [
    (r"D:\Code\AH_analyse", "main"),
    (r"D:\Hermes Agent CN Desktop\data\hermes-home", "main"),
]


def run(cmd, cwd):
    """Run a command, return (returncode, stdout, stderr)."""
    r = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def process_repo(repo_path, branch):
    """处理单个仓库：fetch → status → commit → pull → push。"""
    today = date.today().isoformat()
    lines = []
    repo_name = os.path.basename(repo_path)

    # 1. Fetch
    rc, out, err = run("git fetch origin", repo_path)
    if rc != 0:
        print(f"[{repo_name}] fetch 失败: {err}")
        return False
    lines.append("fetch: ok")

    # 2. Status
    rc, out, err = run("git status --porcelain", repo_path)
    if rc != 0:
        print(f"[{repo_name}] status 失败: {err}")
        return False

    has_changes = bool(out.strip())
    if has_changes:
        lines.append(f"status: {len(out.splitlines())} 项未提交变更")
    else:
        lines.append("status: clean")

    # 3. Commit if needed
    if has_changes:
        rc, out, err = run("git add -A", repo_path)
        if rc != 0:
            print(f"[{repo_name}] add 失败: {err}")
            return False
        lines.append("add: ok")

        msg = f"[auto] daily push {today}"
        rc, out, err = run(f'git commit -m "{msg}"', repo_path)
        if rc != 0:
            print(f"[{repo_name}] commit 失败: {err}")
            return False
        lines.append(f"commit: ok ({msg})")

    # 4. Check if behind remote
    rc, ahead, _ = run("git rev-list --count @{u}..HEAD", repo_path)
    rc2, behind, _ = run("git rev-list --count HEAD..@{u}", repo_path)
    ahead = int(ahead) if ahead.isdigit() else 0
    behind = int(behind) if behind.isdigit() else 0

    if behind > 0:
        rc, out, err = run(f"git pull --rebase origin {branch}", repo_path)
        if rc != 0:
            lines.append(f"pull --rebase: 失败 ({err.strip()})")
        else:
            lines.append("pull --rebase: ok")

    # 5. Push
    rc, out, err = run(f"git push origin {branch}", repo_path)
    if rc != 0:
        if "non-fast-forward" in err.lower() or "rejected" in err.lower():
            lines.append(f"push: 被拒绝 ({err.strip()})")
            print("\n".join(lines))
            print(f"[{repo_name}] 推送被拒绝，需人工处理。")
            return False
        print(f"[{repo_name}] push 失败: {err}")
        return False

    lines.append(f"push: ok → origin/{branch}")

    # 6. Summary
    rc, log, _ = run("git log --oneline -3", repo_path)
    print(f"=== {repo_name} ===")
    print("\n".join(lines))
    print(f"最近提交:\n{log}")
    print()
    return True


def main():
    all_ok = True
    for repo_path, branch in REPOS:
        if not os.path.isdir(repo_path):
            print(f"[跳过] {repo_path} 不是有效目录")
            all_ok = False
            continue
        if not process_repo(repo_path, branch):
            all_ok = False

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()