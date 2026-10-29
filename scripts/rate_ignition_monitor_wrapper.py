#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""利率点火监控 wrapper（cron 入口，watchdog 模式）。

规则：
  - 有 🔥点火 / 🚨熄火 / ✅先行 / ✅起步 任一状态 → 完整推送
  - 状态从"触发"回落到"未触发"（解除）→ 推送一次解除通知
  - 全部信号"未触发/正常"且昨日也全部未触发 → 静默（不推送）
  - 首次运行（无状态文件）→ 推送基线
"""
import json
import subprocess
import sys
from pathlib import Path

MONITOR = r"D:/Code/AH_analyse/tools/rate_ignition_monitor.py"
QUIET_STATE = Path("D:/Code/AH_analyse/tools/rate_ignition_quiet_state.json")
TRIGGER_STATES = ("🔥", "🚨", "✅")


def run_monitor():
    r = subprocess.run([sys.executable, MONITOR, "--json"],
                       capture_output=True, timeout=180)
    if r.returncode != 0:
        print(f"rate_ignition_monitor 执行失败:\n{r.stderr.decode('utf-8', errors='replace')[:500]}")
        sys.exit(1)
    return json.loads(r.stdout.decode("utf-8", errors="replace"))


def main():
    data = run_monitor()
    sigs = data.get("signals", [])
    triggered = [s for s in sigs if any(t in s["state"] for t in TRIGGER_STATES)]
    # 任一信号数据缺失也推送（不静默掩盖故障）
    broken = [s for s in sigs if s["state"] in ("数据缺失",)]

    prev = {}
    if QUIET_STATE.exists():
        try:
            prev = json.loads(QUIET_STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = {}
    had_triggered = prev.get("any_triggered", None)
    prev_names = prev.get("triggered_names", [])

    now_names = sorted(s["key"] for s in triggered)
    cleared = [k for k in prev_names if k not in now_names]

    should_push = (
        triggered or broken or had_triggered is None or cleared
    )

    if should_push:
        r = subprocess.run([sys.executable, MONITOR], capture_output=True, timeout=180)
        print(r.stdout.decode("utf-8", errors="replace"))
        if cleared:
            print(f"\nℹ️ 已解除: {', '.join(cleared)}（状态回落，仅告知一次）")
    else:
        # 静默：更新状态
        pass

    QUIET_STATE.write_text(json.dumps({
        "any_triggered": bool(triggered),
        "triggered_names": now_names,
    }, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
