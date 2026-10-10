# -*- coding: utf-8 -*-
"""Record 成功/失败. Unconfirmed buy orders expire after close by policy."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_account import TICKETS, apply, load, plan, render, today  # noqa: E402
from grid_weixin_ops import fetch_quotes, quotes_are_live  # noqa: E402

TZ = ZoneInfo("Asia/Shanghai")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", choices=["成功", "失败"])
    args = ap.parse_args()
    book, ticket = apply(load(), args.result, today())
    print(render(book, ticket))
    print("")
    print(f"已记账：{args.result}")
    if args.result != "成功":
        return
    if not any(a.get("side") == "sell" for a in ticket.get("actions") or []):
        return
    quotes = fetch_quotes()
    if not quotes:
        print("")
        print("接回单未出：行情失败，盘中检查会再试")
        return
    now = datetime.now(TZ)
    nxt = plan(book, quotes, today(), phase="execute", live=quotes_are_live(quotes, now))
    if nxt.get("status") != "pending" or not nxt.get("actions"):
        return
    nxt["followup"] = True
    (TICKETS / f"{today().isoformat()}.json").write_text(
        json.dumps(nxt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("")
    print(render(book, nxt))


if __name__ == "__main__":
    main()
