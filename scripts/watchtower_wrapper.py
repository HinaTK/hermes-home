#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""观察哨 cron 入口：直接调用 watchtower_monitor（自身已带 watchdog 静默逻辑）。

解释器钉子（蓝本 rate_ignition_monitor_wrapper.py，2026-10-29 cron 部署事故教训：
cron 会话的 sys.executable 不是纯 python，而是 hermes CLI 二进制——
用它起子进程时脚本路径被当成 CLI 参数，argparse 直接拒绝，只吐 usage 文本）。
因此：本 wrapper 接力到系统 312；子进程一律显式 SYSTEM_PY，绝不信任 sys.executable。
"""
import subprocess
import sys

SYSTEM_PY = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
_IS_312 = sys.version_info[:2] == (3, 12) and 'Programs' in sys.executable

if __name__ == '__main__' and not _IS_312:
    import os
    sys.stdout.flush(); sys.stderr.flush()
    sys.exit(subprocess.call([SYSTEM_PY, os.path.abspath(__file__)] + sys.argv[1:]))

MONITOR = r"D:/Code/AH_analyse/tools/watchtower_monitor.py"

r = subprocess.run([SYSTEM_PY, MONITOR], capture_output=True, timeout=300)
out = r.stdout.decode("utf-8", errors="replace")
if out.strip():
    print(out)
if r.returncode != 0:
    print(f"watchtower 执行失败:\n{r.stderr.decode('utf-8', errors='replace')[:400]}")
    sys.exit(1)
