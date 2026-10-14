"""Verify the new per-ETF 5-field summary and grid-letter logic on the real ledger."""
import copy
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import grid_account as g

book = g.load()

print("=== 1. etf_summary (5 data points per ETF) ===")
for code in g.CODES:
    s = g.etf_summary(book, code)
    print(f"{s['code']} {s['name']}")
    print(f"  持有份额={s['holding_qty']:,}  可售份额={s['sellable_qty']:,}  最大格序号={s['max_lot_id']}")
    print(f"  交易记录数={len(s['trades'])}")

print("\n=== 2. sell_target_lot (highest letter still holding shares) ===")
for code in g.CODES:
    pos = book["positions"][code]
    t = g.sell_target_lot(pos)
    print(f"{code}: sell_target={t['id'] if t else None} qty={t['qty'] if t else 0} sell={t['sell'] if t else '-'}")

print("\n=== 3. next_lot_id_after (max letter + 1) ===")
for code in g.CODES:
    pos = book["positions"][code]
    cur = g.max_lot_id(pos)
    print(f"{code}: max={cur} -> next={g.next_lot_id_after(cur)}")

print("\n=== 4. Simulate a sell and verify holding/sellable/max-letter all drop ===")
test = copy.deepcopy(book)
pos = test["positions"]["sh589720"]
before = {l["id"]: l["qty"] for l in pos["lots"]}
print(f"Before: {before} qty={pos['qty']} sellable={g.available(pos, date(2026,10,13))}")

ticket = {"date": "2026-10-13", "phase": "execute", "status": "pending", "actions": [
    {"side": "sell", "code": "sh589720", "qty": 9600, "price": 0.845, "lot": "C-rebuy"}
]}
tmp = tempfile.TemporaryDirectory()
tk = Path(tmp.name) / "tickets"
tk.mkdir()
with patch.object(g, "TICKETS", tk):
    (tk / "2026-10-13.json").write_text(json.dumps(ticket))
    try:
        result_book, result_ticket = g.apply(test, "成功", date(2026, 10, 13))
        pos2 = result_book["positions"]["sh589720"]
        after = {l["id"]: l["qty"] for l in pos2["lots"]}
        print(f"After:  {after} qty={pos2['qty']} sellable={g.available(pos2, date(2026,10,13))}")
        print(f"max_lot_id={g.max_lot_id(pos2)} sell_target={g.sell_target_lot(pos2)['id'] if g.sell_target_lot(pos2) else None}")
        print(f"cash={result_book['cash']}")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        tmp.cleanup()

print("\n=== 5. daily_recompute (T+1 refresh from trade list) ===")
test2 = copy.deepcopy(book)
g.daily_recompute(test2, date(2026, 10, 13))
changed = False
for code in g.CODES:
    for lot in test2["positions"][code]["lots"]:
        print(f"  {code} {lot['id']}: available_from={lot.get('available_from')}")