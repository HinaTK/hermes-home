#!/usr/bin/env python3
"""Gateway auto-heal — check and restart if not running.
Runs via cron every 5 minutes. Silent on success, alerts on restart.
"""

import os
import subprocess
import json
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    r"D:\Hermes Agent CN Desktop\data\hermes-home",
)
GATEWAY_PID_FILE = r"D:\Hermes Agent CN Desktop\data\gateway-runtime\gateway.pid"
HERMES_EXE = r"D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18\hermes-agent-cn-runtime-win32-x64.exe"

CST = timezone(timedelta(hours=8))


def now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def is_gateway_running():
    """Check if gateway process is actually alive via PID file + tasklist."""
    if not os.path.exists(GATEWAY_PID_FILE):
        return False, "PID file missing"

    try:
        with open(GATEWAY_PID_FILE) as f:
            data = json.load(f)
        pid = data.get("pid")
        if not pid:
            return False, "PID file has no pid"

        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        if str(pid) in result.stdout:
            return True, f"pid={pid} alive"
        return False, f"pid={pid} not in process list (stale PID file)"
    except Exception as e:
        return False, f"error checking PID: {e}"


def restart_gateway():
    """Restart gateway via hermes CLI."""
    env = {**os.environ, "HERMES_HOME": HERMES_HOME}
    result = subprocess.run(
        [HERMES_EXE, "gateway", "start"],
        env=env,
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0


def main():
    running, reason = is_gateway_running()
    if running:
        # Silent on success — cron delivers nothing
        return 0

    print(f"[{now_str()}] Gateway not running ({reason}), restarting...")
    if restart_gateway():
        # Verify restart actually worked
        import time
        time.sleep(3)
        running2, reason2 = is_gateway_running()
        if running2:
            print(f"[{now_str()}] ✓ Gateway restarted successfully ({reason2})")
            return 1  # non-zero so cron delivers the alert
        else:
            print(f"[{now_str()}] ✗ Gateway restart failed — still not running ({reason2})")
            return 1
    else:
        print(f"[{now_str()}] ✗ Gateway restart command failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
