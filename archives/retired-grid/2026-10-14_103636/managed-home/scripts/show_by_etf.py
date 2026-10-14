#!/usr/bin/env python3
"""按 ETF 分开展示所有票据操作，去重并标注状态。"""
import json
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

files = sorted(g.TICKETS.glob("*.json"))

# 按 ETF 分组
by_etf = defaultdict(lambda: defaultdict(list))  # code -> date -> [(fname, status, side, lot, qty, price)]

for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    s = t.get("status", "none")
    if s in ("preview", "none"):
        continue
    parts = f.stem.split("-")
    date_str = "-".join(parts[:3])
    for a in t.get("actions", []):
        by_etf[a["code"]][date_str].append((f.name, s, a["side"], a.get("lot") or "", int(a["qty"]), float(a["price"])))

for code in sorted(by_etf):
    print(f"\n{'='*60}")
    print(f"  {code} {g.NAMES[code]}")
    print(f"{'='*60}")
    for date_str in sorted(by_etf[code]):
        ops = by_etf[code][date_str]
        # 去重：相同 side+lot+qty+price 只显示一次，标注出现次数
        seen = {}
        for fname, s, side, lot, qty, px in ops:
            key = (side, lot, qty, px)
            if key not in seen:
                seen[key] = {"count": 0, "statuses": set(), "fnames": []}
            seen[key]["count"] += 1
            seen[key]["statuses"].add(s)
            seen[key]["fnames"].append(fname)

        for (side, lot, qty, px), info in sorted(seen.items()):
            confirmed = "✅" if "成功" in info["statuses"] else ("⚠️" if "已部分成交-归档" in info["statuses"] else "  ")
            dup = f" x{info['count']}" if info["count"] > 1 else ""
            print(f"  {date_str} {confirmed} {side:4s} {lot:14s} {qty:>6,}份 @ {px:.3f}{dup}")