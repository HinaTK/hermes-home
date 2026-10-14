#!/usr/bin/env python3
"""从票据的 partial_fills / filled_action / 已部分成交-归档 字段中提取实际成交记录。"""
import json
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

files = sorted(g.TICKETS.glob("*.json"))

# 1. 从 filled_action 提取（完整成交）
filled = []
for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    fa = t.get("filled_action")
    if fa:
        parts = f.stem.split("-")
        date_str = "-".join(parts[:3])
        filled.append((date_str, f.name, fa))

# 2. 从 partial_fills 提取（部分成交）
partial = []
for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    pf = t.get("partial_fills")
    if pf:
        parts = f.stem.split("-")
        date_str = "-".join(parts[:3])
        if isinstance(pf, list):
            for item in pf:
                partial.append((date_str, f.name, item))
        else:
            partial.append((date_str, f.name, pf))

# 3. 从 status="已部分成交-归档" 的票据中提取 actions
archived = []
for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    if t.get("status") == "已部分成交-归档":
        parts = f.stem.split("-")
        date_str = "-".join(parts[:3])
        for a in t.get("actions", []):
            archived.append((date_str, f.name, a))

print(f"filled_action: {len(filled)} 条")
print(f"partial_fills: {len(partial)} 条")
print(f"已部分成交-归档 actions: {len(archived)} 条")
print()

# 合并去重
all_fills = []
seen = set()
for date_str, fname, item in filled + partial + archived:
    side = item.get("side")
    code = item.get("code")
    lot = item.get("lot", "")
    qty = int(item.get("qty", 0))
    px = float(item.get("price", 0))
    key = (date_str, side, code, lot, qty, px)
    if key in seen:
        continue
    seen.add(key)
    all_fills.append((date_str, fname, item))

# 按 ETF 分组
by_etf = defaultdict(list)
for date_str, fname, item in all_fills:
    by_etf[item["code"]].append((date_str, fname, item))

for code in sorted(by_etf):
    print(f"\n{'='*60}")
    print(f"  {code} {g.NAMES[code]}")
    print(f"{'='*60}")
    items = sorted(by_etf[code], key=lambda x: (x[0], x[2].get("side",""), x[2].get("lot","")))
    for date_str, fname, item in items:
        side = item["side"]
        lot = item.get("lot", "")
        qty = item["qty"]
        px = item["price"]
        extra = ""
        if "limit_price" in item:
            extra += f" 限价{item['limit_price']}"
        if "cost_removed" in item:
            extra += f" 扣成本{item['cost_removed']}"
        if "net_proceeds" in item:
            extra += f" 净回笼{item['net_proceeds']}"
        if "fee" in item:
            extra += f" 费{item['fee']}"
        print(f"  {date_str} {side:5s} {lot:16s} {qty:>6,}份 @ {px:.3f}{extra}  [{fname}]")