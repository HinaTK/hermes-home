#!/usr/bin/env python3
"""虾评打卡：窗口外静默；成功/已打卡/鉴权失败才打印（cron no_agent 空输出不投递）。"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://xiaping.coze.com"
TZ = ZoneInfo("Asia/Shanghai")
TIMEOUT = 20
CTX = ssl.create_default_context()


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        return Path(env)
    return Path(r"D:/Hermes Agent CN Desktop/data/hermes-home")


def load_key() -> str:
    key = os.environ.get("XIAPING_KEY", "").strip()
    if key:
        return key
    env_path = hermes_home() / ".env"
    if not env_path.is_file():
        return ""
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() != "XIAPING_KEY":
            continue
        v = v.strip().strip('"').strip("'")
        return v
    return ""


def request(method: str, path: str, key: str, retry_5xx: bool = True):
    url = API + path
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        data=b"{}" if method == "POST" else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
            raw = resp.read().decode("utf-8", "replace")
            http = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        http = e.code
        if retry_5xx and 500 <= http <= 599:
            return request(method, path, key, retry_5xx=False)
    except Exception as e:
        return 0, {"success": False, "error": type(e).__name__}
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        body = {"success": False, "error": f"non-json HTTP {http}"}
    return http, body if isinstance(body, dict) else {"success": False, "error": "bad-json"}


def out_of_window(http: int, body: dict) -> bool:
    if http == 409:
        return False
    err = str(body.get("error") or "")
    if "不在打卡时间段" in err or "没有可参与的打卡任务" in err:
        return True
    return False


def already(http: int, body: dict) -> bool:
    if http == 409:
        return True
    err = str(body.get("error") or "")
    return "已打卡" in err or "已经打卡" in err


def pick_balance(body: dict):
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    coins = data.get("coins", data.get("balance", data.get("coin")))
    level = data.get("level")
    return coins, level


def main() -> int:
    key = load_key()
    if not key:
        print("虾评打卡失败：未配置密钥")
        return 1

    http_t, tasks = request("GET", "/api/tasks", key)
    if http_t == 401:
        print("虾评打卡失败：鉴权无效（401）")
        return 1
    if http_t >= 500 or http_t == 0:
        print(f"虾评打卡失败：任务列表 HTTP {http_t}")
        return 1

    task_list = []
    data = tasks.get("data")
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        task_list = data["tasks"]
    elif isinstance(data, list):
        task_list = data

    http, body = request("POST", "/api/tasks/checkin", key)
    success = bool(body.get("success")) and http < 400

    if success:
        coins, level = pick_balance(body)
        now = datetime.now(TZ).strftime("%H:%M")
        extra = []
        if coins is not None:
            extra.append(f"余额 {coins}")
        if level:
            extra.append(f"等级 {level}")
        suffix = f"（{'，'.join(extra)}）" if extra else ""
        print(f"虾评打卡成功，北京时间 {now}{suffix}")
        return 0

    if already(http, body):
        return 0

    if out_of_window(http, body) or not task_list:
        return 0

    if http == 401:
        print("虾评打卡失败：鉴权无效（401）")
        return 1

    err = str(body.get("error") or f"HTTP {http}").split("\n", 1)[0][:120]
    print(f"虾评打卡失败：{err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
