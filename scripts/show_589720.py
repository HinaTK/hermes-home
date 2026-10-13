#!/usr/bin/env python3
"""列出 589720 当前账本信息。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

book = g.load()
pos = book["positions"].get("sh589720")

if pos is None:
    print("589720 不在账本中")
    sys.exit(0)

print("=" * 60)
print("  589720 科创创新药ETF国泰")
print("=" * 60)
print(f"  持有份额:  {pos['qty']:>8,} 份")
print(f"  可售份额:  {g.available(pos, g.today()):>8,} 份")
print(f"  最大格号:  {g.max_lot_id(pos) or '-':>8s}")
print(f"  持仓成本:  {pos['cost_cash']:>12,.2f} 元")
print(f"  全账户现金: {book['cash']:>12,.2f} 元")
print()
print(f"  {'格子':16s} {'数量':>8s} {'买入价':>8s} {'卖出价':>8s} {'买入日':>12s} {'T+1可用':>12s}")
print("  " + "-" * 72)
for l in sorted(pos["lots"], key=lambda x: (len(x["id"]), x["id"])):
    print(f"  {l['id']:16s} {l['qty']:>8,} {l['price']:>8.3f} {l.get('sell', 0):>8.3f} {l['bought']:>12s} {l.get('available_from', '-'):>12s}")

# 做T
print()
t = g.t_by_code(book, "sh589720")
print(f"  做T次数: {t['count']}  毛利: {t['gross']:.2f}  扣费: {t['fees']:.2f}  净利: {t['net']:.2f}")
if t["records"]:
    print(f"  {'格子':6s} {'买入日':>12s} {'买价':>8s} {'卖出日':>12s} {'卖价':>8s} {'份额':>8s} {'净利':>10s}")
    for r in t["records"]:
        print(f"  {r['lot']:6s} {r['buy_date']:>12s} {r['buy_price']:>8.3f} {r['sell_date']:>12s} {r['sell_price']:>8.3f} {r['sell_qty']:>8,} {r['net']:>10.2f}")