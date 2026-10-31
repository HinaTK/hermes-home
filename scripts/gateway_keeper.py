#!/usr/bin/env python3
"""网关守护（合并版）——保持网关活着且不异常，每5分钟跑一次。

合并 feishu_health_check.py + gateway_auto_heal.py（2026-10-26 用户要求只留一个）：
1. 进程死了 → 自动重启，重启结果推飞书
2. 配置漂移（FEISHU_GROUP_POLICY=disabled / REQUIRE_MENTION=true）→ 推飞书（进程活着但飞书会哑，必须让人知道）
3. 频道目录缺失 → 推飞书
4. 一切正常 → 完全静默（exit 0 无输出）
去重：同一故障状态文件记录，修复前不重复推（飞书配置类故障去重推每日一次）。

2026-10-31 两代事故教训（同日）：
事故1（04:09-10:04 误报×70）：PID文件位置有两处——网关由桌面App拉起（继承
  HERMES_DESKTOP_* 运行时目录环境变量）时写 data/gateway-runtime/；由计划任务
  .bat/vbs 等干净环境拉起时写 hermes-home/。keeper 只读旧位置拿到死pid=10900，
  又因"PID文件存在但PID已死→直接判死"走不到兜底 → 连续70次误报。
事故2（10:30-10:56 漏报27分钟）：网关109352死亡、桌面App同时重启，其后端
  dashboard 进程与网关**同一个exe名**（hermes-agent-cn-runtime-win32-x64.exe，
  argv=dashboard --host...）。事故1修复引入的"按进程名兜底"把dashboard误认成
  网关 → keeper连续4轮静默，飞书断线27分钟无人管。
定型规则：进程身份必须看**命令行**（含 gateway 才算网关），进程名不可信；
  PID文件覆盖两位置任一活=活；wmic不可用时信任PID文件（网关自己写的）；
  全部不可用 → 判死报警（fail-loud，宁可误报不可再漏报）。
"""

import csv
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    r"D:\Hermes Agent CN Desktop\data\hermes-home",
)
# PID 文件位置取决于**拉起网关的环境**（事故1根因），两处都合法且可能并存：
# - data/gateway-runtime/   桌面App拉起（继承运行时目录env）时写这里
# - hermes-home/gateway.pid 计划任务.bat/vbs 等干净环境拉起时写这里
GATEWAY_PID_FILES = [
    os.path.join(HERMES_HOME, "gateway.pid"),
    r"D:\Hermes Agent CN Desktop\data\gateway-runtime\gateway.pid",
]
GATEWAY_IMAGE = "hermes-agent-cn-runtime-win32-x64.exe"  # 注意：desktop后端(dashboard)同名！
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


def _tasklist(args):
    """tasklist 封装：显式 UTF-8 编码（GBK locale 陷阱），供测试替换。"""
    return subprocess.run(
        ["tasklist"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
    )


def _wmic_processes():
    """列出与网关同名 exe 的全部进程 → [(pid_str, commandline)]；wmic 不可用返回 None。

    这是身份核验的唯一来源：desktop 后端(dashboard)与网关同 exe 名，
    tasklist 按进程名/按PID查只能证明"这个exe活着"，证明不了"网关活着"。
    """
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"name='{GATEWAY_IMAGE}'",
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, timeout=8,
        )
        raw = result.stdout or b""
        if raw[:200].count(b"\x00"):  # wmic 偶发 UTF-16 输出
            text = raw.decode("utf-16-le", errors="replace")
        else:
            text = raw.decode("utf-8", errors="replace")
        procs = []
        reader = csv.reader(io.StringIO(text))
        header = None
        for row in reader:
            if not row:
                continue
            if header is None:
                if "CommandLine" in row and "ProcessId" in row:
                    header = row
                continue
            rec = dict(zip(header, row))
            pid = (rec.get("ProcessId") or "").strip()
            cmd = (rec.get("CommandLine") or "").strip()
            if pid:
                procs.append((pid, cmd))
        return procs
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _is_gateway_cmdline(cmdline):
    """命令行含 gateway 子命令才算网关（dashboard/tui 等同 exe 兄弟进程不含）。"""
    return bool(cmdline) and "gateway" in cmdline.lower()


def _pid_alive(pid):
    """tasklist 按 PID 查存活；返回 (alive, reason)。"""
    try:
        result = _tasklist(["/FI", f"PID eq {pid}", "/NH"])
        if pid and str(pid) in result.stdout:
            return True, f"pid={pid} alive"
    except (OSError, subprocess.SubprocessError):
        pass
    return False, f"pid={pid} not in process list"


def is_gateway_running():
    """网关存活判定（三层）：
    1) PID 文件验活（新旧两位置，网关自己写的记录最权威）：PID 活 = 候选；
       若 wmic 可用且显示该 PID 的命令行不是 gateway（dashboard 顶包/PID 复用）→ 否决该文件；
       wmic 不可用（None）→ 信任 PID 文件（它由网关自己写，含 kind/argv）。
    2) PID 文件全不可用（缺失/死/损坏/被否决）→ wmic 按进程名列全部同名进程，
       任一命令行含 gateway → 活。
    3) wmic 也不可用且无可用 PID 文件 → 判死（fail-loud：10-31 事故2证明
       静默漏报比误报代价大得多）。
    禁止：tasklist 按进程名兜底判活——dashboard 与网关同 exe 名，必误判。
    """
    procs = _wmic_processes()  # None=wmic不可用；[]/[(pid,cmd)...]=查询成功
    for pid_file in GATEWAY_PID_FILES:
        if not os.path.exists(pid_file):
            continue
        try:
            with open(pid_file, encoding="utf-8", errors="replace") as f:
                pid = json.load(f).get("pid")
        except (OSError, ValueError):
            continue  # 文件损坏 → 试下一个位置
        alive, _reason = _pid_alive(pid)
        if not alive:
            continue
        if procs is not None:
            cmdline = dict(procs).get(str(pid))
            if cmdline is not None and not _is_gateway_cmdline(cmdline):
                continue  # PID活着但命令行不是gateway（dashboard顶包/PID复用）→ 不算数
        where = os.path.basename(os.path.dirname(pid_file))
        return True, f"pid={pid} alive ({where}/gateway.pid)"
    if procs:
        for pid, cmdline in procs:
            if _is_gateway_cmdline(cmdline):
                return True, f"pid={pid} alive (cmdline=..., gateway verified, no pid file)"
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
