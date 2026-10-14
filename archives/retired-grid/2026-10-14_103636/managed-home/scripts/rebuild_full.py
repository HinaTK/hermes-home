#!/usr/bin/env python3
"""从所有票据重建完整账本：按日期顺序处理全部非 preview 票据（含 pending 和成功）。

直接操作 book 结构，不调用 apply()（避免迁移守卫和状态检查），
从 seed() 开始，逐笔重放所有历史操作。
"""
import json, copy, sys
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

# 1. 从 seed() 开始（在内存中构建，不写盘）
book = g.seed()
# seed() 的 lot 缺少 available_from，需要补上（与 migrate() 逻辑一致）
for pos in book["positions"].values():
    for lot in pos.get("lots", []):
        if "available_from" not in lot:
            bought = datetime.fromisoformat(lot["bought"]).date()
            lot["available_from"] = g.next_session(bought).isoformat()
# 深拷贝，脱离 seed() 的写盘
book = json.loads(json.dumps(book))

# 预创建 sh589720 空持仓
if "sh589720" not in book["positions"]:
    book["positions"]["sh589720"] = {"lots": [], "qty": 0, "cost_cash": 0.0}

print(f"建仓: 现金 {book['cash']}")
for code in g.CODES:
    pos = book["positions"][code]
    print(f"  {code}: {pos['qty']}份")

# 2. 收集所有票据（跳过 preview 和 none），按日期+文件名排序
files = sorted(g.TICKETS.glob("*.json"))
tickets = []
for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    s = t.get("status", "none")
    if s in ("preview", "none"):
        continue
    parts = f.stem.split("-")
    date_str = "-".join(parts[:3])
    tickets.append((date_str, f.name, t))

# 按日期排序，同日期按文件名
tickets.sort(key=lambda x: (x[0], x[1]))

print(f"\n待处理票据: {len(tickets)} 张")
total_ops = sum(len(t.get("actions", [])) for _, _, t in tickets)
print(f"总操作数: {total_ops} 笔")

# 3. 逐笔处理
errors = []
processed = 0

for date_str, fname, ticket in tickets:
    d_obj = datetime.fromisoformat(date_str).date()
    actions = ticket.get("actions", [])
    if not actions:
        continue

    for i, act in enumerate(actions):
        code = act["code"]
        qty = int(act["qty"])
        px = float(act["price"])
        side = act["side"]
        lot_id = act.get("lot")

        if code not in book["positions"]:
            errors.append(f"{fname}[{i}] {side} {code}: ETF 不在账本中")
            break

        pos = book["positions"][code]
        notional = round(qty * px, 2)
        commission = g.fee(notional)

        if side == "buy":
            cost = round(notional + commission, 2)
            if book["cash"] - cost < -0.01:
                errors.append(f"{fname}[{i}] buy {code} {lot_id} {qty}份@{px}: 现金不足 (需{cost}, 有{book['cash']})")
                break
            book["cash"] = round(book["cash"] - cost, 2)
            pos["qty"] += qty
            pos["cost_cash"] = round(pos["cost_cash"] + cost, 2)
            avail = g.next_session(d_obj).isoformat()
            pos["lots"].append({
                "id": lot_id or g.next_lot_id(pos),
                "qty": qty,
                "price": px,
                "sell": round(px * (1 + g.GAP), 3),
                "bought": date_str,
                "available_from": avail,
            })
            processed += 1

        elif side == "sell":
            # 从目标 lot 直接消耗
            target = next((x for x in pos["lots"] if x["id"] == lot_id), None)
            if target is None:
                errors.append(f"{fname}[{i}] sell {code} {lot_id} {qty}份@{px}: 目标格不存在")
                break
            if int(target["qty"]) < qty:
                errors.append(f"{fname}[{i}] sell {code} {lot_id} {qty}份@{px}: 目标格只有{target['qty']}份")
                break
            if date_str < target.get("available_from", "9999-99-99"):
                errors.append(f"{fname}[{i}] sell {code} {lot_id} {qty}份@{px}: 未过T+1 (可用{target.get('available_from')})")
                break

            target["qty"] = int(target["qty"]) - qty
            proceeds = round(notional - commission, 2)
            book["cash"] = round(book["cash"] + proceeds, 2)
            pos["cost_cash"] = round(pos["cost_cash"] - proceeds, 2)
            g.sync_qty(pos)
            processed += 1

        else:
            errors.append(f"{fname}[{i}] 未知方向 {side}")
            break

    if errors:
        break

if errors:
    print("\n❌ 错误:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print(f"\n共处理 {processed} 笔操作")

# 4. 展示结果
print(f"\n=== 重建后账本 ===")
print(f"history 条数: {len(book['history'])}")
print(f"现金: {book['cash']}")
for code in g.CODES:
    pos = book["positions"][code]
    print(f"\n{code} {g.NAMES[code]}: 持仓 {pos['qty']} 份, 成本 {round(pos['cost_cash'], 2)}")
    for l in sorted(pos["lots"], key=lambda x: (len(x['id']), x['id'])):
        print(f"  {l['id']:14s} {l['qty']:>6,}份 @ {l['price']:.3f} 买入{l.get('bought')} T+1={l.get('available_from')}")

# 做T汇总
t = g.t_total(book)
print(f"\n=== 做T汇总 ===")
print(f"次数: {t['count']}  毛利: {t['gross']}  扣费: {t['fees']}  净利: {t['net']}")

# 5. 写回
g.save(book)
print(f"\n✅ 已写回 ledger.json")