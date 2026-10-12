# -*- coding: utf-8 -*-
"""Intraday: new tickets, or one-shot alert if last crossed a pending limit."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_account import NAMES, TICKETS, load, plan, render, session_phase, today  # noqa: E402
from grid_weixin_ops import fetch_quotes, quotes_are_live  # noqa: E402

TZ = ZoneInfo("Asia/Shanghai")


def fp(ticket) -> str:
    return json.dumps(ticket.get("actions") or [], sort_keys=True, ensure_ascii=False)


def crossed(act, last: float) -> bool:
    px = float(act["price"])
    if act["side"] == "sell":
        return last + 1e-9 >= px
    if act["side"] == "buy":
        return last <= px + 1e-9
    return False


def trend_alert(ticket, quotes, state):
    """Original day-extrema monitor; touch time and broker fills are unknown."""
    from grid_migration import guard_ticket, load_policy
    ticket = guard_ticket(ticket, load_policy(TICKETS.parent / "migration.json"))
    messages = []
    prices = state.setdefault("prices", {})
    alerts = state.setdefault("alerts", {})
    for code in sorted({a["code"] for a in ticket.get("actions") or []}):
        if code not in quotes:
            continue
        last = float(quotes[code]["last"])
        q = quotes[code]
        # Day high/low catch a touch between 10-minute spot snapshots.
        # The vendor does not give the precise touch time; never infer a fill.
        high = float(q["high"]) if q.get("high") else last
        low = float(q["low"]) if q.get("low") else last
        acts = [a for a in ticket.get("actions") or [] if a["code"] == code]
        down = [a for a in acts if a["side"] == "buy" and
                (low <= float(a["price"]) or crossed(a, last))]
        up = [a for a in acts if a["side"] == "sell" and
              (high >= float(a["price"]) or crossed(a, last))]
        name = NAMES.get(code, code)
        for side, hits, extreme in (("down", down, low), ("up", up, high)):
            fresh = []
            for a in sorted(hits, key=lambda x: float(x["price"]), reverse=(side == "down")):
                key = f"{code}:{side}:{a['price']}"
                if not alerts.get(key):
                    alerts[key] = True
                    fresh.append(a)
            if fresh:
                direction = "下探" if side == "down" else "上探"
                label = "最低" if side == "down" else "最高"
                levels = ", ".join(f"{float(a['price']):.3f}（{a['qty']}份）" for a in fresh)
                evidence = f"今日{label}{extreme:.3f}" if q.get("low" if side == "down" else "high") else f"现价{last:.3f}"
                messages.append(f"{name} {evidence}，{direction}{len(fresh)}格观察价：{levels}；现价{last:.3f}。日内极值不能确定触价时刻，可能发生在建议挂单之前，挂单不等于成交，请核对银河委托/成交")
        prices[code] = last
    if not messages:
        return None
    return "\n\n".join(["【连续穿格提醒】"] + messages)


def _load_trend_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"prices": {}, "alerts": {}}


def _save_trend_state(path, state):
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    now = datetime.now(TZ)
    if session_phase(now) != "execute":
        return
    hhmm = now.hour * 100 + now.minute
    if hhmm < 900 or hhmm > 1500:
        return
    quotes = fetch_quotes()
    if not quotes or not quotes_are_live(quotes, now):
        return
    path = TICKETS / f"{today().isoformat()}.json"
    before = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if before and before.get("status") == "pending":
        state_path = TICKETS.parent / "intraday_trend_state.json"
        state = _load_trend_state(state_path)
        if state.get("day") != today().isoformat():
            state = {"day": today().isoformat(), "prices": {}, "alerts": {}}
        trend_msg = trend_alert(before, quotes, state)
        _save_trend_state(state_path, state)
        if trend_msg:
            print(trend_msg)
        return
    book = load()
    ticket = plan(book, quotes, today(), phase="execute", live=True)
    if not ticket.get("actions"):
        return
    if ticket.get("status") != "pending":
        return
    if before and fp(before) == fp(ticket) and before.get("status") in ("成功", "失败"):
        return
    ticket["followup"] = True
    path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    print(render(book, ticket))


if __name__ == "__main__":
    main()
