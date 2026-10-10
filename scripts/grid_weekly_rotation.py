# -*- coding: utf-8 -*-
"""Weekly same-class ETF rotation review; read-only, never places orders."""
from __future__ import annotations

import json
import math
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grid_account import ROOT, is_session_day, migration_policy
from grid_rotation_review import compare_close_proxy, update_consecutive_signal, simulate_daily_grid

TZ = ZoneInfo("Asia/Shanghai")
ROTATION = ROOT / "rotation"
STATE = ROTATION / "weekly-state.json"
CROSS_STATE = ROTATION / "cross-theme-state.json"
BASELINE = "sh589720"
THEMES = {
    "创新药": ["sh589720", "sh589120", "sh515120", "sh516080", "sh517380", "sz159622", "sz159748"],
    "煤炭": ["sh515220"],
    "工业有色": ["sh560860"],
    "宽基": ["sh512100"],
    "传媒": ["sh512980"],
}
# Current live holdings — always compared, never replaced.
HOLDINGS = ["sz159992", "sz159363", "sh589720"]
# Full 321-ETF eligibility pool from grid-broad-20260923/research.py.
# Same scope as the one-shot full-pool ranking; the weekly check just re-runs
# the same trailing-window simulation on whatever is currently eligible.
ELIGIBILITY_CSV = Path(__file__).resolve().parent.parent / "cache" / "grid-broad-20260923" / "eligibility.csv"
CANDIDATES = list(dict.fromkeys(
    [c for codes in THEMES.values() for c in codes if c not in HOLDINGS] + HOLDINGS))
NAMES = {
    "sh589720": "589720 科创创新药ETF国泰",
    "sh589120": "589120 科创创新药ETF汇添富",
    "sh515120": "515120 创新药ETF广发",
    "sh516080": "516080 创新药ETF易方达",
    "sh517380": "517380 创新药ETF天弘",
    "sz159622": "159622 创新药ETF东财",
    "sz159748": "159748 创新药ETF富国",
    "sh515220": "515220 煤炭ETF国泰",
    "sh560860": "560860 工业有色ETF万家",
    "sh512100": "512100 中证1000ETF南方",
    "sh512980": "512980 传媒ETF广发",
}
URL = "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,100,qfq"


def fetch_daily(code: str) -> list[dict]:
    req = urllib.request.Request(URL.format(code=code), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.load(response)
    if payload.get("code") != 0:
        raise ValueError(f"{code} 日线接口失败")
    block = payload.get("data", {}).get(code, {})
    rows = block.get("qfqday") or block.get("day") or []
    bars = [{"date": row[0], "close": float(row[2])} for row in rows]
    if len(bars) < 63 or any(not math.isfinite(x["close"]) or x["close"] <= 0 for x in bars):
        raise ValueError(f"{code} 日线不足63个或价格无效")
    dates = [x["date"] for x in bars]
    if dates != sorted(set(dates)):
        raise ValueError(f"{code} 日线重复或乱序")
    return bars


def compare_themes(all_bars: dict, day: date, themes: dict[str, list[str]] = THEMES) -> dict:
    """Compare each theme on one common window; never infer an order from counts."""
    same_candidates = [x for x in themes["创新药"] if x != BASELINE]
    # Live holdings are always included so the report shows what we actually hold.
    for code in HOLDINGS:
        if code != BASELINE and code not in same_candidates:
            same_candidates.append(code)
    same = compare_close_proxy(all_bars, BASELINE, same_candidates, day)
    # Live holdings are shown for reference but never trigger a switch review.
    base_cycles = same.get("baseline", 0)
    for code in HOLDINGS:
        if code != BASELINE and same.get("leader") == code:
            remaining = [(c, n) for c, n in same["compared"].items()
                         if not c.endswith("_net") and c != BASELINE and c not in HOLDINGS
                         and n > base_cycles]
            remaining.sort(key=lambda x: (-x[1], x[0]))
            if remaining:
                same["leader"] = remaining[0][0]
                same["leader_cycles"] = remaining[0][1]
                same["leader_net"] = same.get("compared_net", {}).get(remaining[0][0])
            else:
                same["leader"] = None
                same["leader_cycles"] = None
                same["leader_net"] = None
    cross_codes = list(dict.fromkeys(code for theme, codes in themes.items()
                                     if theme != "创新药" for code in codes))
    cross = compare_close_proxy(all_bars, BASELINE, cross_codes, day)
    cross["leader_theme"] = next((theme for theme, codes in themes.items()
                                  if cross["leader"] in codes), None) if cross["leader"] else None
    cross["missing"] = [code for code in cross_codes if code not in cross["compared"]]
    cross["executable"] = False
    return {"same_theme": same, "cross_theme": cross}


def main(now: datetime | None = None) -> str:
    now = now or datetime.now(TZ)
    day = now.date()
    if not is_session_day(day) or now.hour * 60 + now.minute < 15 * 60 + 15:
        return "周度轮换检查：收盘未确认或休市，不生成比较"
    policy = migration_policy()
    if not policy or policy.get("target") != BASELINE:
        return "周度轮换检查：589720迁移基准未启用，不改变当前网格"

    # Full 321-ETF eligibility pool, same scope as grid-third-20260930/research.py.
    import pandas as _pd
    _elig = _pd.read_csv(ELIGIBILITY_CSV)
    pool = _elig[_elig.eligible]["code"].tolist()
    names = dict(zip(_elig.code, _elig.name))

    bars = {}
    errors = {}
    for code in pool:
        try:
            bars[code] = fetch_daily(code)
        except Exception as exc:
            errors[code] = f"{type(exc).__name__}: {exc}"
    if BASELINE not in bars:
        raise ValueError("589720当日收盘日线不可用")

    base = bars[BASELINE][-63:]
    dates = [x["date"] for x in base]
    if len(dates) != 63:
        raise ValueError("589720不足63个交易日")

    ranked = []
    for code in pool:
        if code not in bars:
            continue
        keyed = {x["date"]: x for x in bars[code]}
        if any(d not in keyed for d in dates):
            continue
        r = simulate_daily_grid([keyed[d]["close"] for d in dates])
        ranked.append((code, r["cycles"], r["cycle_net"]))
    ranked.sort(key=lambda x: (-x[1], x[0]))

    baseline_cycles = next((n for c, n, _ in ranked if c == BASELINE), 0)
    baseline_net = next((net for c, n, net in ranked if c == BASELINE), 0)

    # Leader = highest-cycle non-holding candidate that beats the baseline.
    leader = None
    for code, cycles, net in ranked:
        if code in HOLDINGS or code == BASELINE:
            continue
        if cycles > baseline_cycles:
            leader = (code, cycles, net)
            break

    # Consecutive-weeks tracking.
    comparison = {
        "baseline": baseline_cycles, "baseline_net": baseline_net,
        "leader": leader[0] if leader else None,
        "leader_cycles": leader[1] if leader else None,
        "leader_net": leader[2] if leader else None,
        "compared": {c: n for c, n, _ in ranked},
        "compared_net": {c: net for c, n, net in ranked},
    }
    signal = update_consecutive_signal(STATE, comparison, day)
    cross_signal = update_consecutive_signal(CROSS_STATE, comparison, day)

    ROTATION.mkdir(parents=True, exist_ok=True)
    (ROTATION / f"{day.isoformat()}.json").write_text(
        json.dumps({**comparison, "names": names, "errors": errors,
                    "asof": day.isoformat(),
                    "consecutive_weeks": signal["consecutive_weeks"],
                    "switch_review_due": signal["switch_review_due"]},
                   ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["【每周全市场ETF轮换检查·仅研究，不自动换仓】",
             "589720仍按迁移计划作为159992替代基准；159992继续停买、停接回、分批退出。",
             f"同一最近63个交易日（约3个月）多槽位网格模拟：{names.get(BASELINE, BASELINE)} "
             f"{baseline_cycles}次往返，净差价约{baseline_net:,.0f}元。"]
    if leader:
        lines.append(f"当前完成往返最多：{names.get(leader[0], leader[0])} "
                     f"{leader[1]}次，净差价约{leader[2]:,.0f}元，高于589720。")
    else:
        lines.append("本周没有候选在可比数据中超过589720。")
    lines.append(f"同一领先者连续周数：{signal['consecutive_weeks']}；"
                 + ("达到连续两周复核门槛，仍不自动换仓。" if signal["switch_review_due"]
                    else "未达到连续两周门槛，不切换。"))

    holding_lines = []
    for code in HOLDINGS:
        c = next((n for c, n, _ in ranked if c == code), None)
        if c is not None:
            holding_lines.append(f"{code} {names.get(code, code)} {c}次")
    if holding_lines:
        lines.append("【当前持仓往返】" + "；".join(holding_lines) +
                     "（仅作参考，不参与领先者判定）")

    top10 = ranked[:10]
    lines.append("【全市场前10】")
    for i, (code, cycles, net) in enumerate(top10, 1):
        tag = " [持仓]" if code in HOLDINGS else ""
        lines.append(f"  {i}. {code} {names.get(code, code)}：{cycles}次，净差价{net:,.0f}元{tag}")

    if errors:
        lines.append(f"数据缺失/失败：{len(errors)}只")
    lines.append("模拟使用收盘价多槽位模型（含T+1、4槽并行、每格5000元），非5分钟成交回测或真实成交；"
                 "绝对数字偏乐观，相对排序可信。不自动买入、不自动撤单、不改变账户10万元和现金底线。")
    return "\n".join(lines)


if __name__ == "__main__":
    print(main())
