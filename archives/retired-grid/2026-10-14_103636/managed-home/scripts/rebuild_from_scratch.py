#!/usr/bin/env python3
"""从建仓开始重建网格账本：seed() → 逐笔 apply 所有已确认票据（status="成功"）。

只处理已确认成交的票据；pending/preview 票据从未实际成交，不参与重建。
多动作票据自动拆分为单笔（迁移期间 apply() 要求每张票据只有一笔操作）。

用法: python rebuild_from_scratch.py [--apply]
  --apply: 将重建结果写回 ledger.json（默认仅对比，不写入）
"""
import json, copy, sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_account as g

APPLY = "--apply" in sys.argv

# 1. 从 seed() 开始（建仓：09-23 首批 A 格）
book = g.seed()
print(f"建仓 seed: 现金 {book['cash']}")
for code in g.CODES:
    pos = book["positions"].get(code)
    if pos:
        print(f"  {code}: {pos['qty']}份 A格@{pos['lots'][0]['price'] if pos['lots'] else 'N/A'}")
    else:
        book["positions"][code] = {"lots": [], "qty": 0, "cost_cash": 0.0}
        print(f"  {code}: (预创建空持仓，建仓时未参与)")

# 2. 收集所有已确认票据（status="成功"），按日期分组
files = sorted(g.TICKETS.glob("*.json"))
by_date = defaultdict(list)
skipped = {"preview": 0, "pending": 0, "none": 0, "失败": 0}
for f in files:
    t = json.loads(f.read_text(encoding="utf-8"))
    s = t.get("status", "none")
    if s != "成功":
        skipped[s] = skipped.get(s, 0) + 1
        continue
    parts = f.stem.split("-")
    date_str = "-".join(parts[:3])
    by_date[date_str].append(f)

print(f"\n待重放已确认票据: {sum(len(v) for v in by_date.values())} 张，覆盖 {len(by_date)} 个日期")
for d in sorted(by_date):
    print(f"  {d}: {len(by_date[d])}张")
print(f"跳过: preview={skipped['preview']} pending={skipped['pending']} none={skipped['none']} 失败={skipped['失败']}")

# 3. 逐笔重放
errors = []
applied_count = 0

# 临时禁用迁移守卫：迁移配置是 09-30 才启用的，09-23~09-29 的历史票据不受此约束
_orig_migration_policy = g.migration_policy
g.migration_policy = lambda: None

for date_str in sorted(by_date):
    if date_str == "2026-09-23":
        print(f"  跳过 {date_str}（建仓已由 seed() 处理）")
        continue

    d_obj = datetime.fromisoformat(date_str).date()
    daily_path = g.TICKETS / f"{date_str}.json"
    backup = daily_path.read_text(encoding="utf-8") if daily_path.exists() else None

    for fname in sorted(by_date[date_str]):
        path = g.TICKETS / fname
        ticket = json.loads(path.read_text(encoding="utf-8"))
        actions = ticket.get("actions", [])
        if not actions:
            continue

        # 多动作票据：拆成单笔逐个 apply（迁移期间 apply() 要求每张票据只有一笔操作）
        for i, act in enumerate(actions):
            single = copy.deepcopy(ticket)
            single["actions"] = [act]
            daily_path.write_text(json.dumps(single, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                book, result = g.apply(book, "成功", d=d_obj)
                applied_count += 1
                print(f"  ✅ {fname}[{i}] {act['side']} {act['code']} {act.get('lot')} {act['qty']}份@{act['price']}")
            except Exception as e:
                errors.append(f"{fname}[{i}] {act['side']} {act['code']} {act.get('lot')} {act['qty']}份@{act['price']}: {e}")
                print(f"  ❌ {fname}[{i}] {act['side']} {act['code']} {act.get('lot')} {act['qty']}份@{act['price']}: {e}")
                break

        if errors:
            break

    if backup:
        daily_path.write_text(backup, encoding="utf-8")
    else:
        daily_path.unlink(missing_ok=True)

    if errors:
        break

# 恢复迁移守卫
g.migration_policy = _orig_migration_policy

if errors:
    print("\n❌ 错误:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print(f"\n共重放 {applied_count} 笔操作")

# 4. 展示结果
print(f"\n=== 重建后账本 ===")
print(f"history 条数: {len(book['history'])}")
print(f"现金: {book['cash']}")
for code in g.CODES:
    pos = book["positions"][code]
    print(f"\n{code} {g.NAMES[code]}: 持仓 {pos['qty']} 份, 成本 {round(pos['cost_cash'], 2)}")
    for l in pos["lots"]:
        print(f"  {l['id']:12s} {l['qty']:>6,}份 @ {l['price']:.3f} 买入{l.get('bought')} T+1={l.get('available_from')}")

# 做T汇总
t = g.t_total(book)
print(f"\n=== 做T汇总 ===")
print(f"次数: {t['count']}  毛利: {t['gross']}  扣费: {t['fees']}  净利: {t['net']}")

if APPLY:
    g.save(book)
    print(f"\n✅ 已写回 ledger.json")
else:
    print(f"\nℹ️  未写入（加 --apply 落盘）")