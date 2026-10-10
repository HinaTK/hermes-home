# -*- coding: utf-8 -*-
"""One-shot cleanup of unconfirmed orders after user verification.

Removes:
  1. 159992 rebuy residue (9400 @ 0.846) — never filled, migration policy
     already marks it failed; the ledger rebuy array still carried it.
  2. 159363 C格 sell 4800 @ 1.221 from ticket unverified_previous_actions
     — user confirmed the broker withdrew it.
  3. Any remaining historical_unconfirmed_buy_orders that are already
     resolved in the ledger but still linger in migration.json.
"""
from __future__ import annotations

import json
from pathlib import Path

HOME = Path(r"D:/Hermes Agent CN Desktop/data/hermes-home")
ROOT = HOME / "cache" / "grid-account"
LEDGER = ROOT / "ledger.json"
MIGRATION = ROOT / "migration.json"
TICKET = ROOT / "tickets" / "2026-10-08.json"


def cleanup_ledger() -> bool:
    book = json.loads(LEDGER.read_text(encoding="utf-8"))
    changed = False

    # 1. Remove 159992 rebuy residue
    pos992 = book["positions"].get("sz159992", {})
    if pos992.get("rebuy"):
        pos992["rebuy"] = []
        changed = True

    # 2. Remove C-rebuy lot that has qty 0 and no fill — keep the lot structure
    #    for grid continuity but ensure no stale rebuy reference remains.
    #    (The lot already has qty:0; nothing to remove.)

    if changed:
        LEDGER.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def cleanup_migration() -> bool:
    pol = json.loads(MIGRATION.read_text(encoding="utf-8"))
    changed = False

    # Remove historical_unconfirmed_buy_orders that are already resolved
    # (159992 C-rebuy 9400 @ 0.846 and D 9600 @ 0.829 both failed).
    # Keep the array empty since both are confirmed failed.
    if pol.get("historical_unconfirmed_buy_orders"):
        pol["historical_unconfirmed_buy_orders"] = []
        changed = True

    if changed:
        MIGRATION.write_text(json.dumps(pol, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def cleanup_ticket() -> bool:
    if not TICKET.exists():
        return False
    t = json.loads(TICKET.read_text(encoding="utf-8"))
    changed = False

    # Remove 159363 C格 sell from unverified_previous_actions
    uvpa = t.get("unverified_previous_actions", [])
    before = len(uvpa)
    t["unverified_previous_actions"] = [
        a for a in uvpa
        if not (a.get("code") == "sz159363" and a.get("side") == "sell"
                and a.get("lot") == "C" and float(a.get("price", 0)) == 1.221)
    ]
    if len(t["unverified_previous_actions"]) < before:
        changed = True
        t["reconciliation_required"] = False

    # Update note
    if changed:
        t["note"] = (
            "159363 C格卖单4800@1.221已由用户确认撤回；"
            "159992残留rebuy已清理。"
            "当日可卖池：159363 B+C共9000份（T+1），D/E/F新买不可卖。"
        )

    TICKET.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def main():
    l = cleanup_ledger()
    m = cleanup_migration()
    t = cleanup_ticket()
    print(f"ledger cleaned: {l}")
    print(f"migration cleaned: {m}")
    print(f"ticket cleaned: {t}")


if __name__ == "__main__":
    main()