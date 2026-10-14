# -*- coding: utf-8 -*-
"""Local grid ledger. User only reports 成功/失败; this file核算."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
HOME = Path(r"D:/Hermes Agent CN Desktop/data/hermes-home")
ROOT = HOME / "cache" / "grid-account"
LEDGER = ROOT / "ledger.json"
TICKETS = ROOT / "tickets"
CODES = ("sz159992", "sz159363", "sh589720")
NAMES = {
    "sz159992": "159992 创新药ETF银华",
    "sz159363": "159363 创业板人工智能ETF华宝",
    "sh589720": "589720 科创创新药ETF国泰",
}
INIT_CASH = 100_000.0
# 10万账户内约8万做网格、2万现金底；账户外另有约8万保护金，不进本账。
# 2026-10-08 用户授权从创新药迁移组合挪6,000元给159363：
# 159992+589720共享40,000元，159363上限40,000元。
CAP = {"sz159992": 40_000.0, "sz159363": 40_000.0, "sh589720": 40_000.0}
TOTAL_CAP = 100_000.0
CASH_FLOOR = 0.0
GAP = 0.015
LOT_BUDGET = {"sz159992": 8_000.0, "sz159363": 6_000.0, "sh589720": 8_000.0}
# Preserve one original build lot as participation inventory in a one-way rise.
# This is a total-share floor, not a particular tax lot or a broker-side restriction.
CORE_QTY = {"sz159992": 9_100, "sz159363": 4_600, "sh589720": 0}
FIRST = {
    "sz159992": {"qty": 9100, "price": 0.871, "second": 9200},
    "sz159363": {"qty": 4600, "price": 1.280, "second": 4700},
}
# A-share cash auction 09:15-09:25; continuous trading from 09:30.
# 09:10 is still pre-auction: last quote is usually yesterday's close.
EXECUTE_HHMM = 931
# SSE 上证公告〔2026〕22号 / 上证公告〔2025〕45号 remaining 2026 closes.
CLOSED_DATES = {
    date(2026, 9, 25),
    date(2026, 9, 26),
    date(2026, 9, 27),
    date(2026, 10, 1),
    date(2026, 10, 2),
    date(2026, 10, 3),
    date(2026, 10, 4),
    date(2026, 10, 5),
    date(2026, 10, 6),
    date(2026, 10, 7),
    date(2026, 10, 10),
}


def today():
    return datetime.now(TZ).date()


def is_session_day(d) -> bool:
    return d.weekday() < 5 and d not in CLOSED_DATES


def session_phase(now=None) -> str:
    now = now or datetime.now(TZ)
    if not is_session_day(now.date()):
        return "closed"
    hhmm = now.hour * 100 + now.minute
    if hhmm < EXECUTE_HHMM:
        return "preview"
    return "execute"


def next_session(d):
    x = d + timedelta(days=1)
    while not is_session_day(x):
        x += timedelta(days=1)
    return x


def fee(notional: float) -> float:
    return max(1.0, round(notional * 0.0001, 2))


def lot_size(budget: float, price: float) -> int:
    qty = int(budget / (price * 100)) * 100
    while qty > 0 and qty * price + fee(qty * price) > budget:
        qty -= 100
    return qty


def load():
    ROOT.mkdir(parents=True, exist_ok=True)
    TICKETS.mkdir(parents=True, exist_ok=True)
    if LEDGER.exists():
        return migrate(json.loads(LEDGER.read_text(encoding="utf-8")))
    return seed()


def migrate(book):
    changed = False
    for pos in book.get("positions", {}).values():
        for lot in pos.get("lots", []):
            if "available_from" not in lot:
                bought = datetime.fromisoformat(lot["bought"]).date()
                lot["available_from"] = next_session(bought).isoformat()
                changed = True
        if "available_from" in pos:
            del pos["available_from"]
            changed = True
        pos.setdefault("rebuy", [])
    if changed:
        save(book)
    return book


def daily_recompute(book, d=None):
    """Recompute sellable quantities from the trade list every day 00:01.

    Each lot's available_from is re-derived from its own buy date in history,
    so a sellable share count is never stale after a day boundary.  Lot ids,
    prices and qtys are preserved; only available_from is refreshed.
    """
    d = d or today()
    changed = False
    for code, pos in book.get("positions", {}).items():
        for lot in pos.get("lots", []):
            bought = datetime.fromisoformat(lot["bought"]).date()
            expected = next_session(bought).isoformat()
            if lot.get("available_from") != expected:
                lot["available_from"] = expected
                changed = True
        sync_qty(pos)
    if changed:
        save(book)
    return book


def save(book):
    ROOT.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
    return book


def seed():
    d = datetime(2026, 9, 23).date()
    book = {
        "opened": d.isoformat(),
        "cash": INIT_CASH,
        "cash_floor": CASH_FLOOR,
        "fee_rule": "万一与每笔最低5元取高；银河ETF最低费未核实",
        "fill_note": "2026-09-23第一批按指导手数入账，成交价用当日14:15快照0.871/1.281；用户未给交割均价",
        "positions": {},
        "history": [],
    }
    for code, spec in FIRST.items():
        qty, px = spec["qty"], spec["price"]
        notional = round(qty * px, 2)
        commission = fee(notional)
        cost = round(notional + commission, 2)
        book["cash"] = round(book["cash"] - cost, 2)
        sell = round(px * (1 + GAP), 3)
        book["positions"][code] = {
            "qty": qty,
            "cost_cash": cost,
            "available_from": next_session(d).isoformat(),
            "second_pending": spec["second"],
            "lots": [
                {
                    "id": "A",
                    "qty": qty,
                    "price": px,
                    "sell": sell,
                    "bought": d.isoformat(),
                }
            ],
        }
        book["history"].append(
            {
                "date": d.isoformat(),
                "result": "成功",
                "assumed": True,
                "actions": [
                    {
                        "side": "buy",
                        "code": code,
                        "qty": qty,
                        "price": px,
                        "fee": commission,
                    }
                ],
            }
        )
    return save(book)


def invested(pos) -> float:
    return round(sum(lot["qty"] * lot["price"] for lot in pos["lots"]), 2)


def sync_qty(pos) -> int:
    """Recompute pos['qty'] from lot qtys. Always call after lot changes."""
    total = sum(int(lot["qty"]) for lot in pos.get("lots", []))
    pos["qty"] = total
    return total


def max_lot_id(pos) -> str | None:
    """Highest grid letter among lots that still hold shares.

    A completed sell zeroes a lot's qty and drops the max grid letter by one;
    the next buy then goes to that freed letter (max + 1).
    """
    letters = []
    for lot in pos.get("lots", []):
        if int(lot.get("qty", 0)) <= 0:
            continue
        lid = str(lot["id"])
        base = lid.split("-")[0]
        if len(base) == 1 and "A" <= base <= "Z":
            letters.append(base)
    if not letters:
        return None
    return max(letters)


def next_lot_id_after(current) -> str:
    """Next grid letter after current (A->B, ..., Z->AA)."""
    if current is None:
        return "A"
    if len(current) == 1 and current < "Z":
        return chr(ord(current) + 1)
    return f"L{len(current) + 1}"


def sell_target_lot(pos):
    """Highest-letter lot that still holds shares (the sell suggestion level)."""
    best = None
    for lot in pos.get("lots", []):
        if int(lot.get("qty", 0)) <= 0:
            continue
        lid = str(lot["id"]).split("-")[0]
        if len(lid) == 1 and "A" <= lid <= "Z":
            if best is None or lid > best[0]:
                best = (lid, lot)
    return best[1] if best else None


def etf_trades(book, code):
    """Trade list for one ETF, derived from the shared history (buy/sell records)."""
    rows = []
    for entry in book.get("history", []):
        for act in entry.get("actions", []):
            if act.get("code") == code:
                rows.append({
                    "date": entry["date"],
                    "result": entry.get("result"),
                    "side": act["side"],
                    "qty": int(act["qty"]),
                    "price": float(act["price"]),
                    "lot": act.get("lot"),
                    "rebuy": bool(act.get("rebuy")),
                    "down_grid": bool(act.get("down_grid")),
                })
    return rows


def etf_summary(book, code, d=None):
    """Five data points per ETF: code, name, holding qty, sellable qty, max grid letter."""
    d = d or today()
    pos = book["positions"][code]
    return {
        "code": code,
        "name": NAMES[code],
        "holding_qty": int(pos["qty"]),
        "sellable_qty": available(pos, d),
        "max_lot_id": max_lot_id(pos),
        "trades": etf_trades(book, code),
    }


def base_lot(lot_id):
    """Base grid letter from a lot id: 'D-rebuy-2' -> 'D', 'G-rebuy' -> 'G', 'C' -> 'C'.

    Returns None for non-letter ids (e.g. 'L8') so they are excluded from T-matching.
    """
    if lot_id is None:
        return None
    base = str(lot_id).split("-")[0]
    if len(base) == 1 and "A" <= base <= "Z":
        return base
    return None


def _t_events(book):
    """Collect buy/sell events grouped by (code, base grid letter), sorted chronologically.

    Returns a fresh copy each call so callers can mutate quantities safely.
    """
    groups = {}
    for entry in book.get("history", []):
        for act in entry.get("actions", []):
            base = base_lot(act.get("lot"))
            if base is None:
                continue
            key = (act["code"], base)
            ev = {
                "date": entry["date"],
                "qty": int(act["qty"]),
                "price": float(act["price"]),
                "lot": act.get("lot"),
                "side": act["side"],
            }
            groups.setdefault(key, []).append(ev)
    for key in groups:
        groups[key].sort(key=lambda x: (x["date"], x["lot"] or ""))
    return groups


def t_records(book):
    """Completed T-trades: same base grid letter buy→sell pairs, FIFO within each letter.

    A T-trade is one buy and one sell at the same grid level.  Repeated T-trades
    on the same letter (e.g. G, G-rebuy, G-rebuy-2) all share the base letter 'G'
    and are matched in chronological order, so they never cross-match.

    Returns a list of dicts, each with buy/sell details, gross, fees and net profit.
    """
    groups = _t_events(book)
    records = []
    for (code, base), evs in sorted(groups.items()):
        buys = [e for e in evs if e["side"] == "buy"]
        sells = [e for e in evs if e["side"] == "sell"]
        bi = 0
        for sell in sells:
            while bi < len(buys) and buys[bi]["qty"] <= 0:
                bi += 1
            if bi >= len(buys):
                break
            buy = buys[bi]
            q = min(buy["qty"], sell["qty"])
            gross = round(q * (sell["price"] - buy["price"]), 2)
            bf = fee(q * buy["price"])
            sf = fee(q * sell["price"])
            records.append({
                "code": code,
                "lot": base,
                "buy_date": buy["date"],
                "buy_price": buy["price"],
                "buy_qty": q,
                "buy_lot": buy["lot"],
                "sell_date": sell["date"],
                "sell_price": sell["price"],
                "sell_qty": q,
                "sell_lot": sell["lot"],
                "gross": gross,
                "fees": round(bf + sf, 2),
                "net": round(gross - bf - sf, 2),
            })
            buy["qty"] -= q
            sell["qty"] -= q
            if buy["qty"] <= 0:
                bi += 1
    return records


def t_total(book):
    """Total T-trade profit summary."""
    recs = t_records(book)
    return {
        "count": len(recs),
        "gross": round(sum(r["gross"] for r in recs), 2),
        "fees": round(sum(r["fees"] for r in recs), 2),
        "net": round(sum(r["net"] for r in recs), 2),
    }


def t_open(book):
    """Unmatched buys per (code, base letter) — current inventory at each grid level.

    Uses the same FIFO matching as t_records(), so completed T-trades are
    deducted before reporting open positions.
    """
    groups = _t_events(book)
    open_pos = {}
    for (code, base), evs in groups.items():
        buys = [e for e in evs if e["side"] == "buy"]
        sells = [e for e in evs if e["side"] == "sell"]
        bi = 0
        for sell in sells:
            while bi < len(buys) and buys[bi]["qty"] <= 0:
                bi += 1
            if bi >= len(buys):
                break
            q = min(buys[bi]["qty"], sell["qty"])
            buys[bi]["qty"] -= q
            sell["qty"] -= q
            if buys[bi]["qty"] <= 0:
                bi += 1
        net = sum(e["qty"] for e in buys if e["qty"] > 0)
        cost = sum(e["qty"] * e["price"] for e in buys if e["qty"] > 0)
        if net > 0:
            open_pos[f"{code}/{base}"] = {
                "code": code,
                "lot": base,
                "qty": net,
                "avg_cost": round(cost / net, 4) if net else 0,
            }
    return open_pos


def t_by_code(book, code):
    """T-trade records and totals for one ETF only."""
    recs = [r for r in t_records(book) if r["code"] == code]
    return {
        "records": recs,
        "count": len(recs),
        "gross": round(sum(r["gross"] for r in recs), 2),
        "fees": round(sum(r["fees"] for r in recs), 2),
        "net": round(sum(r["net"] for r in recs), 2),
    }


def total_invested(book) -> float:
    return round(sum(invested(p) for p in book.get("positions", {}).values()), 2)


def floating_pnl(code: str, pos: dict, last: float) -> float:
    """Per-ETF floating P&L = market_value - cost_cash.

    cost_cash is net invested (total buy costs minus total sell proceeds),
    so this correctly reflects unrealised P&L on remaining shares without
    double-counting completed round trips.  Does NOT include realised P&L
    from history; call realised_pnl() separately for that.
    """
    mv = round(int(pos["qty"]) * last, 2)
    return round(mv - float(pos["cost_cash"]), 2)


def total_floating_pnl(book: dict, quotes: dict) -> float:
    """Sum of per-ETF floating P&L across all positions in the book."""
    total = 0.0
    for code, pos in book.get("positions", {}).items():
        q = quotes.get(code) or {}
        last = float(q.get("last") or 0)
        if last <= 0:
            continue
        total += floating_pnl(code, pos, last)
    return round(total, 2)


def realised_pnl(book: dict) -> float:
    """Cumulative realised P&L from completed history entries.

    Derived from the cash-to-cost_cash gap: cash tracks actual outflows
    and inflows, while cost_cash tracks the net cost basis of remaining
    shares.  The difference is the realised P&L embedded in completed
    round trips (spread + commissions).

    Formula:  realised = current_cash - INIT_CASH + sum(cost_cash)
    """
    total_cost_cash = round(sum(
        float(p.get("cost_cash", 0)) for p in book.get("positions", {}).values()
    ), 2)
    return round(float(book.get("cash", 0)) - INIT_CASH + total_cost_cash, 2)


def available(pos, d) -> int:
    key = d.isoformat()
    return int(sum(lot["qty"] for lot in pos.get("lots", []) if lot["qty"] > 0 and key >= lot.get("available_from", "9999-99-99")))


def migration_policy():
    from grid_migration import load_policy
    return load_policy(TICKETS.parent / "migration.json")


def guard_migration_ticket(ticket):
    from grid_migration import guard_ticket
    return guard_ticket(ticket, migration_policy())


def next_sell_lot(pos, d, code=None):
    """Lowest sell target that the pooled T+1 balance can actually cover.

    The caller (plan) checks available(pos, d) — the pooled T+1 balance —
    against the lot's qty.  A lot bought today cannot itself be sold today,
    but its sell price can be funded by older settled shares.  Filtering on
    available_from here would hide the lowest sell price and force a higher
    target onto the ticket.
    """
    policy = migration_policy()
    core = CORE_QTY.get(code, 0)
    if policy and code == policy["source"] and policy.get("release_source_core"):
        core = 0
    capacity = max(0, int(pos["qty"]) - core) if code else int(pos["qty"])
    eligible = [lot for lot in pos.get("lots", []) if 0 < lot["qty"] <= capacity
                 and lot.get("available_from", "9999-99-99") <= d.isoformat()]
    sellable = available(pos, d)
    actionable = [lot for lot in eligible if int(lot["qty"]) <= sellable]
    if not actionable:
        return None
    # Lowest sell price first; ties broken by oldest settled lot.
    return min(actionable, key=lambda x: (x["sell"], x.get("bought", "")))


def next_lot_id(pos) -> str:
    used = {lot["id"] for lot in pos.get("lots", [])}
    for n in range(26):
        name = chr(ord("A") + n)
        if name not in used:
            return name
    return f"L{len(pos.get('lots', []))}"


def archive_ticket(ticket):
    day = ticket["date"]
    seq = 1
    while (TICKETS / f"{day}-{seq}.json").exists():
        seq += 1
    (TICKETS / f"{day}-{seq}.json").write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")


def write_ticket(day, actions, quotes, extra, phase="execute", live=True):
    ticket = {
        "date": day.isoformat(),
        "quotes": quotes,
        "actions": actions,
        "status": "preview" if phase == "preview" else ("pending" if actions else "none"),
        "phase": phase,
        "live": bool(live),
        "note": extra,
    }
    TICKETS.mkdir(parents=True, exist_ok=True)
    path = TICKETS / f"{day.isoformat()}.json"
    if migration_policy() and path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        ticket["withdrawal_actions"] = list(previous.get("withdrawal_actions", []))
    ticket = guard_migration_ticket(ticket)
    path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    return ticket


def plan(book, quotes, d=None, phase="execute", live=True):
    d = d or today()
    path = TICKETS / f"{d.isoformat()}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        guarded = guard_migration_ticket(existing)
        if guarded != existing:
            archive_ticket(existing)
            existing = guarded
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        if phase == "preview" and existing.get("phase") == "execute":
            return {
                "date": d.isoformat(), "quotes": quotes, "actions": [],
                "status": "preview", "phase": "preview", "live": bool(live),
                "note": "已有当日操作单；仅预告，勿下单",
            }
        locked = existing.get("status") in ("pending", "成功", "失败", "none")
        # Preview must not lock an executable ticket. Execute may replace preview.
        if existing.get("phase") == "execute" and existing.get("status") == "pending":
            stale = False
            for act in existing.get("actions") or []:
                pos = book["positions"].get(act.get("code") or "")
                if not pos:
                    continue
                if act.get("side") == "sell":
                    first = next_sell_lot(pos, d, act.get("code"))
                    if not first or first["id"] != act.get("lot") or int(first["qty"]) != int(act.get("qty") or 0):
                        stale = True
                        break
                    continue
                if act.get("side") != "buy":
                    continue
                lot_id = act.get("lot")
                qty = int(act.get("qty") or 0)
                # An execution can improve on the limit price; match the lot and
                # quantity, not the quote used when the pending ticket was issued.
                if any(
                    x.get("id") == lot_id and int(x.get("qty") or 0) == qty
                    for x in pos.get("lots") or []
                ):
                    stale = True
                    break
            if not stale:
                for code in CODES:
                    pos = book["positions"].get(code)
                    if not pos or not any(x.get("qty", 0) > 0 for x in pos.get("lots") or []):
                        continue
                    buy_actions = [a for a in existing.get("actions") or [] if a.get("code") == code and a.get("side") == "buy" and a.get("down_grid")]
                    if pos.get("rebuy"):
                        rebuy_px = float(pos["rebuy"][0]["price"])
                        next_level = round(rebuy_px / (1 + GAP), 3)
                        pending_prices = {round(float(a["price"]), 3) for a in buy_actions}
                    else:
                        bottom = min((x for x in pos.get("lots") or [] if x.get("qty", 0) > 0), key=lambda x: x["price"], default=None)
                        next_level = round(float(bottom["price"]) / (1 + GAP), 3) if bottom else None
                        pending_prices = {round(float(a["price"]), 3) for a in existing.get("actions") or [] if a.get("code") == code and a.get("side") == "buy"}
                    if next_level is not None:
                        # A rebuy uses the actual (possibly improved) execution
                        # price. Its lower staged grid must survive a refresh.
                        expected = round(next_level, 3)
                        if expected not in pending_prices:
                            stale = True
                            break
            if not stale:
                path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                return existing
            archive_ticket(existing)
        if locked and phase == "preview":
            existing["quotes"] = quotes
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            return existing
    actions = []
    notes = []
    if phase == "preview":
        for code in CODES:
            pos = book["positions"][code]
            last = float(quotes[code]["last"])
            pending = int(pos.get("second_pending") or 0)
            avail = available(pos, d)
            if pending:
                notes.append(
                    f"{NAMES[code]} 拟补第二批约{pending}份，参考价{last}（{'实时' if live else '昨收/盘前'}）；9:31后按开盘实时价重算手数再下单"
                )
            elif avail > 0:
                lot = next_sell_lot(pos, d, code)
                if lot:
                    notes.append(f"{NAMES[code]} 可卖{avail} 卖价={lot['sell']}；9:31前不下单")
                else:
                    notes.append(f"{NAMES[code]} 参与底仓保留不卖；9:31前不下单")
            else:
                notes.append(f"{NAMES[code]} 预告：无动作")
        extra = "；".join(notes)
        extra += "。竞价未结束或开盘实时报价未确认，禁止按此价成交"
        return write_ticket(d, [], quotes, extra, phase="preview", live=live)
    for code in CODES:
        pos = book["positions"][code]
        last = float(quotes[code]["last"])
        avail = available(pos, d)
        cap_left = TOTAL_CAP - total_invested(book)
        pending = int(pos.get("second_pending") or 0)
        policy = migration_policy()
        if policy and code == policy["source"]:
            lot = next_sell_lot(pos, d, code)
            if lot and avail >= int(lot["qty"]):
                actions.append({"side": "sell", "code": code, "qty": int(lot["qty"]),
                                "price": lot["sell"], "lot": lot["id"],
                                "migration_exit": True, "suggested_not_broker_verified": True})
            notes.append(f"{NAMES[code]} 迁移退出：停止新增买入/接回；旧委托先核对，不追买589720")
            continue
        # Finish the two-day build before any grid sell. Day-2 可卖 is T+1 unlock, not a sell instruction.
        if pending and avail > 0 and cap_left > 100:
            qty = min(pending, lot_size(min(8000.0, cap_left), last))
            if qty >= 100 and book["cash"] - (qty * last + fee(qty * last)) >= CASH_FLOOR:
                actions.append(
                    {
                        "side": "buy",
                        "code": code,
                        "qty": qty,
                        "price": last,
                        "lot": "B",
                    }
                )
                notes.append(f"{NAMES[code]} 补第二批{qty} 限价{last}；第一批可卖但不卖")
                continue
        if pending:
            notes.append(f"{NAMES[code]} 建仓未完成，不卖")
            continue
        rebuy = [x for x in pos.get("rebuy", []) if x.get("qty", 0) > 0]
        rebuy_reserved = 0.0
        rebuy_invested = 0.0
        if rebuy:
            target = rebuy[0]
            qty = int(target["qty"])
            px = float(target["price"])
            cost = qty * px + fee(qty * px)
            if book["cash"] - cost >= CASH_FLOOR - 1e-6 and total_invested(book) + qty * px <= TOTAL_CAP + 1e-6:
                actions.append({
                    "side": "buy", "code": code, "qty": qty, "price": px,
                    "lot": f"{target['from_lot']}-rebuy" if target.get("from_lot") else next_lot_id(pos),
                    "rebuy": True,
                })
                rebuy_reserved = cost
                rebuy_invested = qty * px
                notes.append(f"{NAMES[code]} 接回{qty} 限价{px}（不到价不买）")
            else:
                notes.append(f"{NAMES[code]} 接回受现金/上限限制")
        sellable = next_sell_lot(pos, d, code)
        working = [lot for lot in pos.get("lots", []) if lot["qty"] > 0]
        sellable_qty = available(pos, d)
        if sellable and sellable_qty > 0 and sellable_qty >= sellable["qty"]:
            top = sellable
            actions.append(
                {
                    "side": "sell",
                    "code": code,
                    "qty": top["qty"],
                    "price": top["sell"],
                    "lot": top["id"],
                    "resting": True,
                }
            )
            notes.append(f"{NAMES[code]} 挂卖{top['id']}格{top['qty']} 限价{top['sell']}")
        # 最大序号格子卖出建议 / 最大序号+1 买入建议（每次开盘及买卖后均给出）
        cur_max = max_lot_id(pos)
        if cur_max:
            cur_lot = sell_target_lot(pos)
            if cur_lot:
                if sellable_qty >= int(cur_lot["qty"]):
                    notes.append(f"{NAMES[code]} 最大{cur_lot['id']}格卖出建议：{int(cur_lot['qty'])}份 限价{cur_lot['sell']}（可售{sellable_qty}份，足够）")
                else:
                    notes.append(f"{NAMES[code]} 最大{cur_lot['id']}格卖出建议：{int(cur_lot['qty'])}份 限价{cur_lot['sell']}（可售{sellable_qty}份，不足，暂不建议）")
                next_id = next_lot_id_after(cur_max)
                next_px = round(float(cur_lot["price"]) / (1 + GAP), 3)
                next_qty = lot_size(LOT_BUDGET[code], next_px)
                notes.append(f"{NAMES[code]} 最大{next_id}格买入建议：约{next_qty}份 限价{next_px}")
        # 做T汇总：同格反复做T按 base 格子（G / G-rebuy / G-rebuy-2）归并，不重复计数
                tc = t_by_code(book, code)
                if tc["count"]:
                    notes.append(f"{NAMES[code]} 做T累计：{tc['count']}次 毛利{tc['gross']}元 扣费{tc['fees']}元 净利{tc['net']}元")
                open_t = t_open(book)
                for k, v in open_t.items():
                    if v["code"] == code:
                        notes.append(f"{NAMES[code]} {v['lot']}格未平仓T：{v['qty']}份 均价{v['avg_cost']}")
        # A pending rebuy already occupies the single buy slot for this ETF;
        # do not stage additional down-grid buys on the same ticket.
        if rebuy:
            continue
        if working:
            # Do not impose a calendar-day one-grid cap. If price has crossed
            # several lower levels, stage each crossed level, subject to the
            # cash floor and per-ETF cap. This matches the user's priority:
            # turnover first, risk limits second.
            bottom = min(working, key=lambda x: x["price"])
            # A completed sell may be rebought at a better execution price than
            # the old bottom's theoretical grid. Stage the next level below that
            # rebuy rather than recreating the already-completed D grid.
            level_px = round((float(rebuy[0]["price"]) if rebuy else float(bottom["price"])) / (1 + GAP), 3)
            staged = 0
            staged_cash = book["cash"] - rebuy_reserved
            staged_invested = invested(pos) + rebuy_invested
            next_id = next_lot_id(pos)
            while staged == 0 or (level_px >= last - 1e-9 and staged < 12):
                qty = lot_size(LOT_BUDGET[code], level_px)
                cost = qty * level_px + fee(qty * level_px) if qty else 0
                if (
                    qty < 100
                    or staged_cash - cost < CASH_FLOOR - 1e-6
                    or total_invested(book) + staged_invested - invested(pos) + qty * level_px > TOTAL_CAP + 1e-6
                ):
                    notes.append(f"{NAMES[code]} 第{staged + 1}个下行格受现金/上限限制")
                    break
                actions.append(
                    {
                        "side": "buy",
                        "code": code,
                        "qty": qty,
                        "price": level_px,
                        "lot": next_id,
                        "down_grid": True,
                    }
                )
                notes.append(f"{NAMES[code]} 挂买{next_id}格{qty} 限价{level_px}")
                staged += 1
                staged_cash -= cost
                staged_invested += qty * level_px
                next_id = chr(ord(next_id) + 1) if len(next_id) == 1 else f"L{staged}"
                level_px = round(level_px / (1 + GAP), 3)
            if staged == 0:
                notes.append(f"{NAMES[code]} 下一格尚未跌到，暂不补仓")
        if not sellable and not working:
            notes.append(f"{NAMES[code]} 今无指令")
    extra = "；".join(notes)
    return write_ticket(d, actions, quotes, extra, phase="execute", live=live)


def apply(book, result: str, d=None):
    d = d or today()
    path = TICKETS / f"{d.isoformat()}.json"
    if not path.exists():
        raise FileNotFoundError(f"无当日指令 {path}")
    ticket = json.loads(path.read_text(encoding="utf-8"))
    if ticket.get("phase") == "preview" or ticket.get("status") == "preview":
        raise ValueError("9:10预告不可记账，等9:31可执行单")
    if ticket["status"] in ("成功", "失败", "none"):
        return book, ticket
    if result == "失败":
        ticket["status"] = "失败"
        path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        book["history"].append({"date": d.isoformat(), "result": "失败", "actions": ticket["actions"]})
        return save(book), ticket
    if result != "成功":
        raise ValueError("只要成功或失败")
    if migration_policy() and len(ticket.get("actions", [])) != 1:
        raise ValueError("迁移期间成交必须逐笔确认代码、方向、份额和均价，不能整张票据记成功")
    for act in ticket["actions"]:
        code, qty, px = act["code"], int(act["qty"]), float(act["price"])
        pos = book["positions"][code]
        notional = round(qty * px, 2)
        commission = fee(notional)
        if act["side"] == "buy":
            cost = round(notional + commission, 2)
            if book["cash"] - cost < CASH_FLOOR - 1e-6:
                raise ValueError("现金不足，未入账")
            if total_invested(book) + notional > TOTAL_CAP + 1e-6:
                raise ValueError("超成本上限，未入账")
            book["cash"] = round(book["cash"] - cost, 2)
            pos["qty"] += qty
            pos["cost_cash"] = round(pos["cost_cash"] + cost, 2)
            pos["lots"].append(
                {
                    "id": act.get("lot") or next_lot_id(pos),
                    "qty": qty,
                    "price": px,
                    "sell": round(px * (1 + GAP), 3),
                    "bought": d.isoformat(),
                    "available_from": next_session(d).isoformat(),
                }
            )
            if act.get("rebuy"):
                pos["rebuy"] = [x for x in pos.get("rebuy", []) if not (int(x["qty"]) == qty)]
            if act.get("lot") == "B":
                pos["second_pending"] = max(0, int(pos.get("second_pending") or 0) - qty)
        elif act["side"] == "sell":
            policy = migration_policy()
            exiting = bool(policy and code == policy["source"])
            if not exiting and int(pos["qty"]) - qty < CORE_QTY[code]:
                ticket["core_breached"] = True
            sellable_qty = available(pos, d)
            if sellable_qty < qty:
                raise ValueError("可卖不足，未入账")
            proceeds = round(notional - commission, 2)
            book["cash"] = round(book["cash"] + proceeds, 2)

            # 1) Consume the sold shares from the named target lot directly.
            #    The user's rule: a sell reduces holding shares, reduces
            #    sellable shares, and drops the max grid letter by one when
            #    the top lot empties.  The named lot IS the source.
            target_lot_id = act.get("lot")
            target = next((x for x in pos["lots"] if x["id"] == target_lot_id), None)
            if target is None or int(target["qty"]) < qty:
                raise ValueError("目标格份额不足，未入账")
            if d.isoformat() < target.get("available_from", "9999-99-99"):
                raise ValueError("目标格未过T+1，未入账")
            target["qty"] = int(target["qty"]) - qty

            # 2) cost_cash = net invested: total buy costs minus total sell
            #    proceeds.  This matches the user's cost basis model, where
            #    a sell does not reduce the cost basis of remaining shares.
            pos["cost_cash"] = round(pos["cost_cash"] - proceeds, 2)

            # 3) pos['qty'] must equal sum of lot qtys.
            sync_qty(pos)

            if not exiting:
                rebuy_px = round(float(act["price"]) / (1 + GAP), 3)
                pos.setdefault("rebuy", []).append({"qty": qty, "price": rebuy_px, "from_lot": act.get("lot")})
    ticket["status"] = "成功"
    archive_ticket(ticket)
    path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    book["history"].append({"date": d.isoformat(), "result": "成功", "actions": ticket["actions"]})
    return save(book), ticket


def render(book, ticket) -> str:
    ticket = guard_migration_ticket(ticket)
    d = ticket["date"]
    phase = ticket.get("phase") or "execute"
    live = ticket.get("live")
    tag = "昨收/盘前" if live is False else "实时"
    if phase == "preview":
        lines = [f"【预告】{d} 竞价未结束或实时报价未确认 勿下单"]
    else:
        title = "盘中" if ticket.get("followup") else "9:31后可执行"
        lines = ["**现在的剩余操作建议**", f"【操作】{d} {title}"]
        for code in CODES:
            acts = [a for a in ticket["actions"] if a["code"] == code]
            rows = [f"**{NAMES[code]}**"]
            for side in ("sell", "buy"):
                for act in acts:
                    if act["side"] == side:
                        label = "卖" if side == "sell" else "买"
                        grid = f" {act['lot']} 格" if act.get("lot") else ""
                        rows.append(f"- {label}{grid}：**{int(act['qty']):,} 份 @ {float(act['price']):.3f}**")
            if len(rows) > 1:
                lines.append("\n".join(rows))
        if not ticket["actions"]:
            lines.append("无新增操作")
        if ticket.get("core_breached"):
            lines.append("【警报】底仓已被实际成交耗尽；券商旧单须核对，次日勿自动追买。")
        from grid_migration import migration_note
        note = migration_note(migration_policy())
        if note:
            lines.append(note)
        lines.append("限价单；先核对银河已有委托，勿重复挂单。挂单不等于成交。")
        return "\n\n".join(lines)
    for code in CODES:
        q = ticket["quotes"][code]
        pos = book["positions"][code]
        name = NAMES[code]
        lines += [f"{name} {tag}{q['last']} 昨收{q['prev']}"]
        acts = [a for a in ticket["actions"] if a["code"] == code]
        if phase == "preview":
            pending = int(pos.get("second_pending") or 0)
            avail = available(pos, datetime.fromisoformat(d).date())
            if pending:
                lines += ["今：不下单", f"拟补第二批约{pending}份，9:31按开盘价重算"]
            elif avail > 0:
                lot = next_sell_lot(pos, datetime.fromisoformat(d).date(), code)
                lines += [f"今：不下单 可卖{avail} 卖价={lot['sell']}" if lot else "今：不下单 参与底仓保留不卖"]
            else:
                lines += ["今：不下单"]
            continue
        if not acts:
            avail = available(pos, datetime.fromisoformat(d).date())
            pending = int(pos.get("second_pending") or 0)
            if pending and avail <= 0:
                lines += ["今：不卖不买", "补仓：否（T+1未到）"]
            elif pending:
                lines += ["今：不卖（建仓未完成）", "补仓：等指令"]
            elif avail <= 0:
                lines += ["今：不卖不买", "补仓：否"]
            else:
                lot = next_sell_lot(pos, datetime.fromisoformat(d).date(), code)
                lines += [f"今：可卖{avail} 卖价={lot['sell']}", "补仓：否"] if lot else ["今：参与底仓保留不卖", "补仓：否"]
        else:
            for a in acts:
                if a["side"] == "sell":
                    lines += [f"挂卖：{a['qty']}份 限价{a['price']} 不到不成交"]
                else:
                    kind = "接回" if a.get("rebuy") else ("下一格" if a.get("down_grid") else "补仓")
                    lines += [f"挂买{kind}：{a['qty']}份 限价{a['price']} 不到不成交"]
    lines += ["禁：当日新买不卖", "禁：账户现金不低于2万", "禁：不超成本上限"]
    if phase == "preview":
        lines += ["9:25竞价结束 9:30连续竞价；实时报价未确认则勿下单"]
    elif ticket["actions"]:
        lines += ["回：成功 或 失败"]
    # WeChat ilink collapses single newlines into spaces; keep a blank line between rows.
    return "\n\n".join(lines)
