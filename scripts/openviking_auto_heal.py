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
    try:
        subprocess.Popen(
            [SERVER_EXE, "--host", HOST, "--port", str(PORT)],
            cwd=OV_HOME,
            env=env,
            creationflags=DETACHED_FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"launch failed: {type(exc).__name__}: {exc}"
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
            return 1  # non-zero keeps the restart alert visible for cron delivery

    healthy3, detail3 = is_healthy()
    if healthy3:
        print(f"[{now_str()}] ✓ OpenViking restarted (late) — {detail3}")
        return 1
    print(
        f"[{now_str()}] ✗ OpenViking still unhealthy {START_TIMEOUT_S}s "
        f"after restart — manual check needed ({detail3})"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
