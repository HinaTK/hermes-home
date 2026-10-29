#!/usr/bin/env python3
"""网关守护（合并版）——保持网关活着且不异常，每5分钟跑一次。

合并 feishu_health_check.py + gateway_auto_heal.py（2026-10-26 用户要求只留一个）：
1. 进程死了 → 自动重启，重启结果推飞书
2. 配置漂移（FEISHU_GROUP_POLICY=disabled / REQUIRE_MENTION=true）→ 推飞书（进程活着但飞书会哑，必须让人知道）
3. 频道目录缺失 → 推飞书
4. 一切正常 → 完全静默（exit 0 无输出）
去重：同一故障状态文件记录，修复前不重复推（飞书配置类故障去重推每日一次）。
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
GATEWAY_PID_FILE = r"D:\Hermes Agent CN Desktop\data\gateway-runtime\gateway.pid"
HERMES_EXE = r"D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18\hermes-agent-cn-runtime-win32-x64.exe"
ENV_FILE = os.path.join(HERMES_HOME, ".env")
CHANNEL_DIR = os.path.join(HERMES_HOME, "channel_directory.json")
STATE_FILE = os.path.join(HERMES_HOME, "cache", "gateway-keeper-state.json")

CST = timezone(timedelta(hours=8))


def now_str():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now(CST).strftime("%Y-%m-%d")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def is_gateway_running():
    """进程存活：PID file + tasklist 验证，缺PID文件时按进程名兜底。"""
    if os.path.exists(GATEWAY_PID_FILE):
        try:
            with open(GATEWAY_PID_FILE) as f:
                pid = json.load(f).get("pid")
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if pid and str(pid) in result.stdout:
                return True, f"pid={pid} alive"
            return False, f"pid={pid} not in process list"
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hermes-agent-cn-runtime-win32-x64.exe", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if lines and "hermes" in lines[0].lower():
            parts = lines[0].split()
            return True, f"pid={parts[1]} alive (tasklist fallback)"
    except (OSError, subprocess.SubprocessError):
        pass
    return False, "no gateway process found"


def check_env():
    """飞书配置漂移：进程活着但群聊会被静默吞掉的配置。"""
    if not os.path.exists(ENV_FILE):
        return "❌ .env 文件缺失"
    with open(ENV_FILE, encoding="utf-8", errors="replace") as f:
        content = f.read()
    if "FEISHU_GROUP_POLICY=disabled" in content:
        return "❌ FEISHU_GROUP_POLICY=disabled（群聊被禁用）"
    if "FEISHU_REQUIRE_MENTION=true" in content:
        return "❌ FEISHU_REQUIRE_MENTION=true（需要@才响应）"
    return None


def check_channel_dir():
    if not os.path.exists(CHANNEL_DIR):
        return "❌ channel_directory.json 缺失"
    try:
        with open(CHANNEL_DIR, encoding="utf-8") as f:
            data = json.load(f)
        groups = [c for c in data.get("platforms", {}).get("feishu", []) if c.get("type") == "group"]
        if groups:
            return None
        return "❌ 频道目录里没有飞书群"
    except (OSError, ValueError):
        return "❌ channel_directory.json 解析失败"


def restart_gateway():
    env = {**os.environ, "HERMES_HOME": HERMES_HOME}
    try:
        result = subprocess.run(
            [HERMES_EXE, "gateway", "start"],
            env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main():
    state = load_state()
    messages = []

    # 1) 进程检查 + 自愈
    running, reason = is_gateway_running()
    if not running:
        line = f"[{now_str()}] 网关未运行（{reason}），正在重启..."
        print(line)
        if restart_gateway():
            import time
            time.sleep(3)
            running2, reason2 = is_gateway_running()
            if running2:
                print(f"[{now_str()}] ✓ 网关重启成功（{reason2}）")
            else:
                print(f"[{now_str()}] ✗ 重启后仍不运行（{reason2}），需要人工介入")
        else:
            print(f"[{now_str()}] ✗ 重启命令执行失败，需要人工介入")
        return 1  # 进程级故障必推

    # 2) 配置/频道检查（进程活着但飞书哑）——当日去重
    config_faults = [msg for msg in (check_env(), check_channel_dir()) if msg]
    if config_faults:
        key = "; ".join(config_faults)
        if state.get("config_fault_key") != key or state.get("config_fault_day") != today():
            print(f"[{now_str()}] ⚠️ 网关进程正常但飞书配置异常（当日去重，修复前明日再提醒）：")
            for msg in config_faults:
                print(f"  {msg}")
            state["config_fault_key"] = key
            state["config_fault_day"] = today()
            save_state(state)
            return 1
        return 0  # 同一故障当日已推过，静默

    # 3) 全部正常：清状态、完全静默
    if state:
        state.pop("config_fault_key", None)
        state.pop("config_fault_day", None)
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
