#!/usr/bin/env python3
"""Feishu gateway health check — runs every 5 minutes via cron.

Checks:
1. Gateway process is running (PID file + tasklist fallback)
2. FEISHU_GROUP_POLICY is not 'disabled'
3. FEISHU_REQUIRE_MENTION is not 'true'
4. Gateway log shows recent feishu connection
5. Channel directory has the expected group channel

If any check fails, prints a clear alert. No side effects — read-only.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    r"D:\Hermes Agent CN Desktop\data\hermes-home",
)
GATEWAY_PID = r"D:\Hermes Agent CN Desktop\data\gateway-runtime\gateway.pid"
GATEWAY_LOG = os.path.join(HERMES_HOME, "logs", "gateway.log")
CHANNEL_DIR = os.path.join(HERMES_HOME, "channel_directory.json")
ENV_FILE = os.path.join(HERMES_HOME, ".env")

CST = timezone(timedelta(hours=8))


def now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def check_pid_file():
    """Check if gateway process is running (via PID file or tasklist fallback)."""
    # Try PID file first
    if os.path.exists(GATEWAY_PID):
        try:
            with open(GATEWAY_PID) as f:
                data = json.load(f)
            pid = data.get("pid")
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq hermes*", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            if pid and str(pid) in result.stdout:
                return True, f"pid={pid} alive"
            return False, f"pid={pid} not found in process list"
        except Exception:
            pass  # fall through to tasklist

    # Fallback: check tasklist directly for hermes-gateway process
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hermes-agent-cn-runtime-win32-x64.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if lines:
            parts = lines[0].split()
            if len(parts) >= 2:
                pid = parts[1]
                return True, f"pid={pid} alive (no PID file, tasklist fallback)"
        return False, "no gateway process found"
    except Exception as e:
        return False, f"error: {e}"


def check_env():
    """Check FEISHU_GROUP_POLICY and FEISHU_REQUIRE_MENTION."""
    issues = []
    if not os.path.exists(ENV_FILE):
        return False, ".env missing"
    with open(ENV_FILE) as f:
        content = f.read()
    if "FEISHU_GROUP_POLICY=disabled" in content:
        issues.append("FEISHU_GROUP_POLICY=disabled (group chat blocked)")
    if "FEISHU_REQUIRE_MENTION=true" in content:
        issues.append("FEISHU_REQUIRE_MENTION=true (requires @mention)")
    if issues:
        return False, "; ".join(issues)
    return True, "OK"


def check_recent_feishu():
    """Check if gateway log has recent feishu activity."""
    if not os.path.exists(GATEWAY_LOG):
        return False, "gateway.log missing"
    try:
        mtime = os.path.getmtime(GATEWAY_LOG)
        age_min = (datetime.now().timestamp() - mtime) / 60
        if age_min > 10:
            return False, f"log stale ({age_min:.0f}min old)"
        with open(GATEWAY_LOG, errors="replace") as f:
            lines = f.readlines()[-50:]
        has_connected = any("feishu connected" in l for l in lines)
        has_group = any("feishu:group" in l for l in lines[-20:])
        if not has_connected:
            return False, "no recent feishu connection"
        return True, f"connected, group_activity={'yes' if has_group else 'no (may be idle)'}"
    except Exception as e:
        return False, f"error: {e}"


def check_channel_dir():
    """Check channel directory has feishu group."""
    if not os.path.exists(CHANNEL_DIR):
        return False, "channel_directory.json missing"
    try:
        with open(CHANNEL_DIR) as f:
            data = json.load(f)
        feishu_channels = data.get("platforms", {}).get("feishu", [])
        group_channels = [c for c in feishu_channels if c.get("type") == "group"]
        if group_channels:
            return True, f"{len(group_channels)} group channel(s)"
        return False, "no group channel in directory"
    except Exception as e:
        return False, f"error: {e}"


def main():
    print(f"=== Feishu Health Check [{now_str()}] ===")

    checks = [
        ("Gateway PID", check_pid_file),
        ("Env config", check_env),
        ("Feishu log", check_recent_feishu),
        ("Channel dir", check_channel_dir),
    ]

    all_ok = True
    for name, fn in checks:
        ok, msg = fn()
        status = "✅" if ok else "❌"
        if not ok:
            all_ok = False
        print(f"  {status} {name}: {msg}")

    if all_ok:
        print("  ✅ All checks passed")
    else:
        print("  ❌ ISSUES DETECTED")
        print("     Fix: FEISHU_GROUP_POLICY=open, FEISHU_REQUIRE_MENTION=false, restart gateway")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
