#!/usr/bin/env python3
"""按用户指令重建 589720 账本：纯 A-Z 序列号，买入=max+1，卖出=max 格消耗后 max-1。"""
import json, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

book = g.load()
print(f"当前: 现金 {book['cash']:.2f}")

if "sh589720" not in book["positions"]:
    book["positions"]["sh589720"] = {"lots": [], "qty": 0, "cost_cash": 0.0}
else:
    # 清空旧 lot，从建仓重建
    book["positions"]["sh589720"] = {"lots": [], "qty": 0, "cost_cash": 0.0}
    # 现金恢复到 seed() 状态
    book["cash"] = 86183.90

code = "sh589720"
pos = book["positions"][code]

# 用户指令的交易（按顺序，只有方向+数量+价格）
trades = [
    ("2026-10-08", "buy",  9200, 0.877),
    ("2026-10-08", "buy",  9400, 0.859),
    ("2026-10-08", "buy",  9600, 0.829),
    ("2026-10-09", "sell", 9600, 0.846),
    ("2026-10-12", "buy",  9600, 0.833),
    ("2026-10-12", "buy",  9900, 0.806),
    ("2026-10-12", "buy", 10000, 0.794),
    ("2026-10-12", "sell",10000, 0.806),
    ("2026-10-12", "sell", 9900, 0.818),
]

for date_str, side, qty, px in trades:
    d_obj = datetime.fromisoformat(date_str).date()
    notional = round(qty * px, 2)
    commission = g.fee(notional)

    if side == "buy":
        cur_max = g.max_lot_id(pos)
        next_id = chr(ord(cur_max) + 1) if cur_max else "A"
        cost = round(notional + commission, 2)
        book["cash"] = round(book["cash"] - cost, 2)
        pos["qty"] += qty
        pos["cost_cash"] = round(pos["cost_cash"] + cost, 2)
        avail = g.next_session(d_obj).isoformat()
        pos["lots"].append({
            "id": next_id, "qty": qty, "price": px,
            "sell": round(px * (1 + g.GAP), 3),
            "bought": date_str, "available_from": avail,
        })
        print(f"  ✅ {date_str} 买 {next_id}格 {qty:>6,}份 @ {px:.3f}  成本{cost:.2f}  现金{book['cash']:.2f}")

    elif side == "sell":
        # 卖最大序号且有持仓的格子（不是所有lot中最高字母）
        sellable_max = max((l["id"] for l in pos["lots"] if int(l["qty"]) > 0), default=None)
        if sellable_max is None:
            print(f"  ❌ {date_str} 卖: 无持仓可卖")
            sys.exit(1)
        target = next((x for x in pos["lots"] if x["id"] == sellable_max), None)
        if target is None or int(target["qty"]) < qty:
            print(f"  ❌ {date_str} 卖 {sellable_max}格: 份额不足")
            sys.exit(1)
        target["qty"] = int(target["qty"]) - qty
        proceeds = round(notional - commission, 2)
        book["cash"] = round(book["cash"] + proceeds, 2)
        pos["cost_cash"] = round(pos["cost_cash"] - proceeds, 2)
        g.sync_qty(pos)
        print(f"  ✅ {date_str} 卖 {sellable_max}格 {qty:>6,}份 @ {px:.3f}  回笼{proceeds:.2f}  现金{book['cash']:.2f}")

g.save(book)

print(f"\n=== 589720 最终 ===")
print(f"持有份额: {pos['qty']:,}  可售: {g.available(pos, g.today()):,}  最大格号: {g.max_lot_id(pos)}")
print(f"成本: {pos['cost_cash']:.2f}  现金: {book['cash']:.2f}")
for l in sorted(pos["lots"], key=lambda x: (len(x["id"]), x["id"])):
    print(f"  {l['id']}格 {l['qty']:>6,}份 @ {l['price']:.3f} 买入{l['bought']} T+1={l['available_from']}")