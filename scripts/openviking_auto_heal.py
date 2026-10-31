#!/usr/bin/env python3
"""OpenViking auto-heal — check health and restart the server if down.

Runs via Hermes cron every 5 minutes. Silent on success (empty stdout =
nothing delivered); prints an alert only when a restart was attempted or
failed, so cron delivers the alert to Feishu.

Restarts the server directly as a detached process (does NOT depend on the
Windows scheduled task or supervisor, which can silently lose registration).
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

OV_HOME = r"C:\Users\Administrator\.openviking"
SERVER_EXE = os.path.join(OV_HOME, "venv", "Scripts", "openviking-server.exe")
CONFIG_FILE = os.path.join(OV_HOME, "ov.conf")
CLI_CONFIG_FILE = os.path.join(OV_HOME, "ovcli.conf")
HEALTH_URL = "http://127.0.0.1:1933/health"
HOST = "127.0.0.1"
PORT = 1933
START_TIMEOUT_S = 45  # server can take ~10s to bind; allow margin

CST = timezone(timedelta(hours=8))

# Detach so the server survives this short-lived cron process.
DETACHED_FLAGS = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | subprocess.CREATE_NO_WINDOW
)


def now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def is_healthy():
    """Return (healthy, detail)."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") == "ok" and payload.get("healthy") is True:
            return True, f"version={payload.get('version', '?')}"
        return False, f"unhealthy payload: {payload}"
    except Exception as exc:  # noqa: BLE001 - any transport failure = down
        return False, f"{type(exc).__name__}: {exc}"


def start_server():
    """Launch openviking-server detached. Returns (ok, detail)."""
    if not os.path.exists(SERVER_EXE):
        return False, f"server exe missing: {SERVER_EXE}"
    env = os.environ.copy()
    env["OPENVIKING_CONFIG_FILE"] = CONFIG_FILE
    env["OPENVIKING_CLI_CONFIG_FILE"] = CLI_CONFIG_FILE
    log_fh = None
    try:
        # 2026-10-31: 服务器输出不再吞进 DEVNULL——崩溃原因下次有据可查
        # 2026-10-31 事故2: 此处曾写 OV_HOME / "logs" / ... 而 OV_HOME 是 str，
        # 抛 TypeError 使重启在落盘阶段就崩 → 守卫自己变成故障点。一律 os.path.join。
        log_dir = os.path.join(OV_HOME, "logs")
        os.makedirs(log_dir, exist_ok=True)
        server_log = os.path.join(log_dir, "server-autoheal.log")
        log_fh = open(server_log, "ab")
        subprocess.Popen(
            [SERVER_EXE, "--host", HOST, "--port", str(PORT)],
            cwd=OV_HOME,
            env=env,
            creationflags=DETACHED_FLAGS,
            stdout=log_fh,
            stderr=log_fh,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"launch failed: {type(exc).__name__}: {exc}"
    finally:
        # 子进程已继承句柄；父进程必须关掉，否则每次重启漏一个句柄（测试里表现为临时目录删不掉）
        if log_fh is not None:
            log_fh.close()
    return True, "launched"


def main():
    healthy, detail = is_healthy()
    if healthy:
        # Silent on success — cron delivers nothing.
        return 0

    print(f"[{now_str()}] OpenViking DOWN ({detail}), restarting...")
    ok, launch_detail = start_server()
    if not ok:
        print(f"[{now_str()}] ✗ OpenViking restart failed: {launch_detail}")
        return 1

    deadline = time.time() + START_TIMEOUT_S
    while time.time() < deadline:
        time.sleep(3)
        healthy2, detail2 = is_healthy()
        if healthy2:
            print(
                f"[{now_str()}] ✓ OpenViking restarted successfully "
                f"({launch_detail}, {detail2})"
            )
            return 0  # 2026-10-31: 重启成功=成功。exit 1 会让 cron 标"script failed"误导用户（stdout 照常推送重启事件）

    healthy3, detail3 = is_healthy()
    if healthy3:
        print(f"[{now_str()}] ✓ OpenViking restarted (late) — {detail3}")
        return 0  # 2026-10-31: 同上——晚到恢复也是自愈成功，返回 1 会被 cron 标 failed
    print(
        f"[{now_str()}] ✗ OpenViking still unhealthy {START_TIMEOUT_S}s "
        f"after restart — manual check needed ({detail3})"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
