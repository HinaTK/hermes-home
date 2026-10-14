"""TDD test: 589720 ledger from user's confirmed data."""
import json, sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

# User's confirmed 589720 trades (in order)
TRADES = [
    ("buy",  9200, 0.877, "A"),
    ("buy",  9400, 0.859, "B"),
    ("buy",  9600, 0.829, "C"),
    ("sell", 9600, 0.846, "C"),
    ("buy",  9600, 0.833, "C-rebuy"),
    ("buy",  9900, 0.806, "D"),
    ("buy", 10000, 0.794, "E"),
    ("sell",10000, 0.806, "E"),
    ("sell", 9900, 0.818, "D"),
]

def build_book():
    book = g.seed()
    if "sh589720" not in book["positions"]:
        book["positions"]["sh589720"] = {"lots": [], "qty": 0, "cost_cash": 0.0}
    book["positions"]["sz159992"] = {"lots": [], "qty": 0, "cost_cash": 0.0}
    book["positions"]["sz159363"] = {"lots": [], "qty": 0, "cost_cash": 0.0}
    book["cash"] = 100000.0
    book["history"] = []
    return book

def apply_trades(book, trades):
    d = date(2026, 10, 8)
    for side, qty, px, lot in trades:
        pos = book["positions"]["sh589720"]
        notional = round(qty * px, 2)
        commission = g.fee(notional)
        if side == "buy":
            cost = round(notional + commission, 2)
            book["cash"] = round(book["cash"] - cost, 2)
            pos["qty"] += qty
            pos["cost_cash"] = round(pos["cost_cash"] + cost, 2)
            avail = g.next_session(d).isoformat()
            pos["lots"].append({
                "id": lot, "qty": qty, "price": px,
                "sell": round(px * (1 + g.GAP), 3),
                "bought": d.isoformat(), "available_from": avail,
            })
            book["history"].append({
                "date": d.isoformat(), "result": "成功",
                "actions": [{"side": "buy", "code": "sh589720",
                             "qty": qty, "price": px, "lot": lot}],
            })
        elif side == "sell":
            target = next((x for x in pos["lots"] if x["id"] == lot), None)
            assert target is not None, f"lot {lot} not found"
            assert int(target["qty"]) >= qty, f"lot {lot} has {target['qty']} < {qty}"
            target["qty"] = int(target["qty"]) - qty
            proceeds = round(notional - commission, 2)
            book["cash"] = round(book["cash"] + proceeds, 2)
            pos["cost_cash"] = round(pos["cost_cash"] - proceeds, 2)
            g.sync_qty(pos)
            book["history"].append({
                "date": d.isoformat(), "result": "成功",
                "actions": [{"side": "sell", "code": "sh589720",
                             "qty": qty, "price": px, "lot": lot}],
            })
        d = g.next_session(d)
    return book

# Build and apply
book = build_book()
book = apply_trades(book, TRADES)

print("=== 589720 持仓 ===")
pos = book["positions"]["sh589720"]
print(f"持仓: {pos['qty']} 份")
print(f"成本: {round(pos['cost_cash'], 2)}")
print(f"现金: {book['cash']}")
print()
for l in sorted(pos["lots"], key=lambda x: (len(x['id']), x['id'])):
    print(f"  {l['id']:16s} {l['qty']:>6,}份 @ {l['price']:.3f}  T+1={l.get('available_from')}")

# 做T
print()
print("=== 做T记录 ===")
recs = g.t_records(book)
for r in recs:
    print(f"  {r['code']} {r['lot']}格: 买{r['buy_date']}@{r['buy_price']} {r['buy_qty']}份({r['buy_lot']}) -> 卖{r['sell_date']}@{r['sell_price']} {r['sell_qty']}份({r['sell_lot']})  净{r['net']}")

t = g.t_total(book)
print(f"  总计: {t['count']}次 毛利{t['gross']} 扣费{t['fees']} 净利{t['net']}")

# 未平仓T
print()
print("=== 未平仓T ===")
open_t = g.t_open(book)
for k, v in sorted(open_t.items()):
    print(f"  {k}: {v['qty']}份 均价{v['avg_cost']}")

# Assertions
print()
print("=== 断言检查 ===")
# Final holdings: A:9200 + B:9400 + C-rebuy:9600 = 28200
assert pos["qty"] == 28200, f"Expected 28200, got {pos['qty']}"
# T-trades: C buy 9600@0.829 -> sell 9600@0.846 (1 trade)
# E buy 10000@0.794 -> sell 10000@0.806 (1 trade)
# D buy 9900@0.806 -> sell 9900@0.818 (1 trade)
# Total: 3 T-trades
assert t["count"] == 3, f"Expected 3 T-trades, got {t['count']}"
print(f"✅ 全部通过: 持仓{pos['qty']}份, 做T {t['count']}次, 净利{t['net']}")
