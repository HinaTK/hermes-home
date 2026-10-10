# -*- coding: utf-8 -*-
"""Daily grid ops ticket from local ledger. User confirms fills separately."""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_account import apply, is_session_day, load, plan, render, session_phase, today  # noqa: E402

TZ = ZoneInfo("Asia/Shanghai")
URL = "https://qt.gtimg.cn/q=sz159992,sz159363,sh589720"


def fetch_quotes():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode("gbk", errors="replace")
    out = {}
    for code in ("sz159992", "sz159363", "sh589720"):
        m = re.search(rf'v_{code}="([^"]*)"', raw)
        if not m:
            return None
        p = m.group(1).split("~")
        out[code] = {
            "last": p[3],
            "prev": p[4],
            "open": p[5] if len(p) > 5 else "",
            "time": p[30] if len(p) > 30 else "",
            "high": p[33] if len(p) > 33 else "",
            "low": p[34] if len(p) > 34 else "",
        }
    return out


def quotes_are_live(quotes, now) -> bool:
    """True only if vendor timestamp is at/after 09:30 on this session."""
    if not quotes:
        return False
    day = now.strftime("%Y%m%d")
    for q in quotes.values():
        ts = str(q.get("time") or "")
        if len(ts) < 12 or not ts.startswith(day):
            return False
        if int(ts[8:12]) < 930:
            return False
    return True


def with_evening_review(text, day, phase):
    """Append a dated, non-executable after-close review; never alter actions."""
    from grid_eod_decision import POLICY_VERSION, load_for_session, next_day_note
    report = load_for_session(day)
    if report and report.get("policy_version") != POLICY_VERSION:
        return text + "\n\n【昨收旧版评估已失效】策略规则已更新；只核对当前票据与银河在途单。"
    if report and report.get("history_count") is not None and len(load().get("history", [])) != report["history_count"]:
        return text + "\n\n【昨收评估已失效】收盘后有新成交入账；须重新核对银河和当日操作单。"
    note = next_day_note(report, day, phase) if report else ""
    return text + "\n\n" + note if note else text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", choices=["成功", "失败"])
    ap.add_argument("--phase", choices=["auto", "preview", "execute"], default="auto")
    args = ap.parse_args()
    now = datetime.now(TZ)
    # Explicit --phase must not bypass exchange holiday/session gating.
    if not args.result and not is_session_day(now.date()):
        return
    phase = session_phase(now) if args.phase == "auto" else args.phase
    if phase == "closed" and not args.result:
        print("今日休市，无操作")
        return
    book = load()
    if args.result:
        book, ticket = apply(book, args.result, today())
        print(render(book, ticket))
        print("")
        print(f"已记账：{args.result}")
        return
    quotes = fetch_quotes()
    if not quotes:
        print("行情获取失败，今日不操作")
        return
    live = quotes_are_live(quotes, now)
    if phase == "execute" and not live:
        ticket = plan(book, quotes, today(), phase="preview", live=False)
        print(with_evening_review(render(book, ticket), today(), "preview"))
        return
    if phase != "execute":
        ticket = plan(book, quotes, today(), phase="preview", live=live)
    else:
        ticket = plan(book, quotes, today(), phase="execute", live=True)
    print(with_evening_review(render(book, ticket), today(), phase))


if __name__ == "__main__":
    main()
