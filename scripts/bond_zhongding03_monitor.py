"""中鼎转03 (sz127119) 上市监控：上市日提醒 + 首日卖出提醒。

用户 2026-10-26 中签中鼎转03（1手=10张，面值100元/张），要求上市可卖时单独提醒卖出。
数据源：腾讯行情 qt.gtimg.cn（与网格系统同源）。
判定上市：行情时间戳为当前交易日且 last != 100.000（上市前腾讯返回面值100占位）。
只提醒一次（状态文件去重）。
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CODE = "sz127119"
NAME = "中鼎转03"
STATE_PATH = Path("D:/Hermes Agent CN Desktop/data/hermes-home/cache/grid-account/bond-127119-monitor.json")
TZ = timezone(timedelta(hours=8))


def fetch_quote():
    url = f"https://qt.gtimg.cn/q={CODE}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        text = response.read().decode("gbk", errors="replace")
    match = re.search(rf'v_{CODE}="([^"]*)"', text)
    if not match:
        raise ValueError("腾讯行情缺少127119")
    fields = match.group(1).split("~")
    if len(fields) < 35:
        raise ValueError("腾讯行情字段不足")
    return dict(name=fields[1], last=fields[3], prev=fields[4],
                 high=fields[33], low=fields[34], time=fields[30])


def is_trading_day(date):
    # 周末不交易；节假日按需补充（当前窗口内无节假日）
    return date.weekday() < 5


def monitor(now=None):
    now = now or datetime.now(TZ)
    state = {}
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not is_trading_day(now.date()):
        return None
    try:
        quote = fetch_quote()
    except Exception as error:  # 行情失败不报障、不写状态
        print(f"行情获取失败，跳过本轮：{error}", file=sys.stderr)
        return None
    today = now.date().isoformat()
    if state.get("listed") or state.get("alerted_day") == today:
        return None
    stamp = str(quote["time"])
    is_today = stamp.startswith(today.replace("-", "")) and stamp[8:10] >= "09"
    last = float(quote["last"])
    high = float(quote["high"] or 0)
    if is_today and (last != 100.000 or high > 0):
        state["listed"] = today
        state["first_quote"] = quote
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"【中签债券上市提醒】中鼎转03(127119) 今日上市可卖！现价={quote['last']}，最高={quote['high']}，最低={quote['low']}，腾讯时间={quote['time']}。你中签1手(10张)，达到心理价位即可卖出；上市首日转债无涨跌幅停牌(深市临停规则除外)，请按银河账户实际持仓操作。"
    # 未上市：静默
    return None


if __name__ == "__main__":
    message = monitor()
    if message:
        print(message)
