# -*- coding: utf-8 -*-
"""After-close uptrend review; read-only advice, never modifies orders or ledger."""
from __future__ import annotations

import json
import math
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grid_account import CORE_QTY, GAP, LOT_BUDGET, NAMES, ROOT, is_session_day, load, lot_size, next_session, migration_policy
from grid_rotation_review import assess_low_efficiency, completed_cycles
from grid_weixin_ops import fetch_quotes

TZ = ZoneInfo("Asia/Shanghai")
POLICY_VERSION = "rotation-efficiency-v1"
STORE = ROOT / "eod"
URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,80,qfq"


def fetch_daily(code: str) -> list[dict]:
    req = urllib.request.Request(URL.format(code=code), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.load(response)
    if data.get("code") != 0:
        raise ValueError(f"{code} 日线接口失败")
    item = data.get("data", {}).get(code, {})
    rows = item.get("qfqday") or item.get("day") or []
    bars = [{"date": row[0], "close": float(row[2])} for row in rows]
    if len(bars) < 25 or any(not math.isfinite(bar["close"]) or bar["close"] <= 0 for bar in bars):
        raise ValueError(f"{code} 日线不足或价格无效")
    if [bar["date"] for bar in bars] != sorted({bar["date"] for bar in bars}):
        raise ValueError(f"{code} 日线重复或乱序")
    return bars


def assess(code: str, book: dict, bars: list[dict], day: date) -> dict:
    if len(bars) < 25 or bars[-1]["date"] != day.isoformat():
        raise ValueError(f"{code} 缺少当日已确认收盘日线")
    closes = [float(row["close"]) for row in bars]
    if any(not math.isfinite(x) or x <= 0 for x in closes):
        raise ValueError(f"{code} 收盘价无效")
    close = closes[-1]
    policy = migration_policy()
    if policy and code == policy["source"]:
        return {"state": "MIGRATION_EXIT", "executable": False, "close": close,
                "reason": "迁移退出：停止新增买入/接回；旧委托待核对，589720迁入尚未启用"}
    result = {"state": "HOLD_GRID", "executable": False, "close": close,
              "reason": "原2%网格保持，不追涨；有持仓继续按既有目标卖出，卖后按实际成交价接回"}
    pos = book["positions"][code]
    cycle_review = assess_low_efficiency(
        completed_cycles(book, code), bars, day, gap=GAP
    )
    result["efficiency"] = cycle_review
    if cycle_review["state"] == "LOW_EFFICIENCY":
        result["state"] = "ROTATION_REVIEW"
        result["reason"] = "网格效率预警：" + cycle_review["reason"] + "；仅提示研究替代ETF，不自动换仓"
        return result
    # Start the review *before* the last tradable grid is sold, so a rising
    # market still has a strategic participation core rather than zero shares.
    low_inventory = CORE_QTY[code] + lot_size(LOT_BUDGET[code], close)
    if int(pos["qty"]) > low_inventory:
        result["reason"] = "仍高于参与底仓加一格，优先用原网格周转"
        return result
    events = [(idx, act) for idx, item in enumerate(book.get("history", []))
              if item.get("result") == "成功" for act in item.get("actions", [])
              if act.get("code") == code and act.get("side") in ("sell", "buy")]
    sells = [(idx, act) for idx, act in events if act["side"] == "sell"]
    if not sells:
        result["reason"] = "没有已确认卖出，不用假定的触价作为上移锚点"
        return result
    sell_idx, sale = sells[-1]
    if any(idx > sell_idx and act["side"] == "buy" for idx, act in events):
        result["reason"] = "最近卖出后已接回/加仓，继续原网格"
        return result
    sale_price = float(sale["price"])
    if (close <= sale_price * (1 + GAP)
            or close <= sum(closes[-20:]) / 20
            or sum(closes[-20:]) <= sum(closes[-25:-5])):
        result["reason"] = "尚未在单次收盘高于已确认卖价2%，或20日均线未走高；先保留参与底仓"
        return result
    if close > sum(closes[-20:]) / 20 * 1.08:
        result["state"] = "WAIT_PULLBACK"
        result["reason"] = "离20日均线超过8%，暂不追高"
        return result
    # Price is a watch level, not a resting order. Prefer a pullback to avoid
    # converting a grid system into a market-price breakout chase.
    result.update(state="REVIEW_REBASE", watch_price=math.floor(close / (1 + GAP) * 1000) / 1000,
                  reference_sale=sale_price,
                  reason="低库存且单次收盘高于已确认卖价2%，20日均线上行；仅供提前复核，不自动上移或买入"
                         + ("；原接回记录及券商在途买单须先核对，不可叠加新买" if pos.get("rebuy") else ""))
    return result


def cleanup_after_close(book: dict) -> bool:
    """Remove unconfirmed buy orders and zero-qty rebuy residue.

    Called from the 15:20 EOD task after the session closes.  It does NOT
    touch the ledger's cash, qty, or cost_cash — only stale bookkeeping
    fields that could confuse the next day's plan().
    """
    changed = False
    policy = migration_policy()
    if policy and policy.get("historical_unconfirmed_buy_orders"):
        policy["historical_unconfirmed_buy_orders"] = []
        (ROOT / "migration.json").write_text(
            json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        changed = True
    for pos in book.get("positions", {}).values():
        rebuy = pos.get("rebuy")
        if rebuy:
            kept = [r for r in rebuy if int(r.get("qty", 0)) > 0]
            if len(kept) != len(rebuy):
                pos["rebuy"] = kept
                changed = True
    return changed


def next_day_note(report: dict, day: date, phase: str) -> str:
    if report.get("for_session") != day.isoformat():
        return ""
    lines = ["【昨收上移基准评估·仅供复核，勿按候选价下单】"]
    for code, item in report.get("decisions", {}).items():
        policy = migration_policy()
        if policy and code == policy["source"]:
            lines.append(f"{NAMES[code]}：迁移退出；停买/停接回，旧委托待核对，589720迁入尚未启用。")
            continue
        state = item["state"]
        label = {"REVIEW_REBASE": "低库存上移候选", "WAIT_PULLBACK": "过热等回踩", "HOLD_GRID": "维持原网格", "ROTATION_REVIEW": "网格效率预警，研究替代"}.get(state, "数据不足")
        efficiency = item.get("efficiency", {})
        suffix = (f"；20日完成{efficiency['cycles_20d']}次、10日完成{efficiency['cycles_10d']}次、"
                  f"网格穿越{efficiency['crossings']}次" if efficiency else "")
        extra = f"；观察回踩价{item['watch_price']:.3f}（非委托价）" if state == "REVIEW_REBASE" else ""
        lines.append(f"{NAMES[code]}：{label}{extra}{suffix}；{item.get('reason', '需核对原网格及当日行情')}")
    lines.append("券商在途委托和当日成交须先核对；旧单不自动撤改，9:31开盘后实时报价仍需复核。")
    return "\n".join(lines)


def load_for_session(day: date) -> dict | None:
    prev = day
    for _ in range(12):
        from datetime import timedelta
        prev -= timedelta(days=1)
        if is_session_day(prev):
            path = STORE / f"{prev.isoformat()}.json"
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if data.get("for_session") == day.isoformat() else None
    return None


def main(now: datetime | None = None) -> str:
    now = now or datetime.now(TZ)
    day = now.date()
    if not is_session_day(day) or now.hour * 60 + now.minute < 15 * 60 + 15:
        return "收盘未确认或休市：不生成上移决策"
    quotes = fetch_quotes()
    if not quotes:
        raise ValueError("收盘行情不可用，不生成上移决策")
    book = load()
    # Clean up unconfirmed orders and rebuy residue after session close
    cleanup_after_close(book)
    decisions = {}
    for code in NAMES:
        stamp = str(quotes.get(code, {}).get("time") or "")
        if not stamp.startswith(day.strftime("%Y%m%d")) or len(stamp) < 12 or int(stamp[8:12]) < 1500:
            raise ValueError(f"{code} 未得到当日收盘确认行情")
        bars = fetch_daily(code)
        qclose = float(quotes[code]["last"])
        if abs(bars[-1]["close"] - qclose) > max(0.002, qclose * 0.005):
            raise ValueError(f"{code} 日线与收盘快照不一致")
        decisions[code] = assess(code, book, bars, day)
    report = {"asof": day.isoformat(), "for_session": next_session(day).isoformat(),
              "policy_version": POLICY_VERSION,
              "history_count": len(book.get("history", [])),
              "quote_times": {code: quotes[code]["time"] for code in NAMES},
              "source": "腾讯日线(day/qfqday)与收盘快照交叉检查；不代表银河成交/委托", "decisions": decisions}
    STORE.mkdir(parents=True, exist_ok=True)
    (STORE / f"{day.isoformat()}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return next_day_note(report, next_session(day), "preview")


if __name__ == "__main__":
    print(main())
