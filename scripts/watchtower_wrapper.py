#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""观察哨 cron 入口：直接调用 watchtower_monitor（自身已带 watchdog 静默逻辑）。"""
import subprocess
import sys

r = subprocess.run([sys.executable, r"D:/Code/AH_analyse/tools/watchtower_monitor.py"],
                   capture_output=True, timeout=300)
out = r.stdout.decode("utf-8", errors="replace")
if out.strip():
    print(out)
if r.returncode != 0:
    print(f"watchtower 执行失败:\n{r.stderr.decode('utf-8', errors='replace')[:400]}")
    sys.exit(1)
