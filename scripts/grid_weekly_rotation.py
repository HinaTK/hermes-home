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
from grid_rotation_review import compare_close_proxy, update_consecutive_signal

TZ = ZoneInfo("Asia/Shanghai")
ROTATION = ROOT / "rotation"
STATE = ROTATION / "weekly-state.json"
CROSS_STATE = ROTATION / "cross-theme-state.json"
BASELINE = "sh589720"
THEMES = {
    "创新药": [BASELINE, "sh589120", "sh515120", "sh516080", "sh517380", "sz159622", "sz159748"],
    "煤炭": ["sh515220"],
    "工业有色": ["sh560860"],
    "宽基": ["sh512100"],
    "传媒": ["sh512980"],
}
CANDIDATES = THEMES["创新药"][1:]
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
URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,100,qfq"


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
    same = compare_close_proxy(all_bars, BASELINE,
                               [x for x in themes["创新药"] if x != BASELINE], day)
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
    bars = {}
    errors = {}
    for code in dict.fromkeys(code for codes in THEMES.values() for code in codes):
        try:
            bars[code] = fetch_daily(code)
        except Exception as exc:
            errors[code] = f"{type(exc).__name__}: {exc}"
    if BASELINE not in bars:
        raise ValueError("589720当日收盘日线不可用")
    screens = compare_themes(bars, day)
    result = screens["same_theme"]
    cross = screens["cross_theme"]
    result["names"] = {code: NAMES.get(code, code) for code in result["compared"]}
    result["errors"] = errors
    result["migration"] = "159992继续退出；589720仍为迁入基准；本报告不启用买入"
    result["source"] = "腾讯复权日线；同一63个交易日、2%收盘价往返代理，不代表真实5分钟成交"
    signal = update_consecutive_signal(STATE, result, day)
    result.update({"consecutive_weeks": signal["consecutive_weeks"],
                   "switch_review_due": signal["switch_review_due"]})
    cross_signal = update_consecutive_signal(CROSS_STATE, cross, day)
    cross.update({"consecutive_weeks": cross_signal["consecutive_weeks"],
                  "switch_review_due": cross_signal["switch_review_due"]})
    result["cross_theme"] = cross
    ROTATION.mkdir(parents=True, exist_ok=True)
    (ROTATION / f"{day.isoformat()}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    compared = result["compared"]
    compared_net = result.get("compared_net", {})
    lines = ["【每周同类与跨题材ETF轮换检查·仅研究，不自动换仓】",
             "589720仍按迁移计划作为159992替代基准；159992继续停买、停接回、分批退出。",
             f"同一最近63个交易日（约3个月）多槽位网格模拟：{NAMES[BASELINE]} "
             f"{compared[BASELINE]}次往返，净差价约{compared_net.get(BASELINE, 0)}元。"]
    leader = result.get("leader")
    if leader:
        lines.append(f"当前完成往返最多：{NAMES.get(leader, leader)} "
                     f"{compared[leader]}次，净差价约{compared_net.get(leader, 0)}元，高于589720。")
    else:
        lines.append("本周没有同类ETF在可比数据中超过589720。")
    lines.append(f"同一创新药领先者连续周数：{result['consecutive_weeks']}；"
                 + ("达到同类复核门槛，仍不自动换仓。" if result["switch_review_due"]
                    else "未达到连续两周门槛，不切换。"))
    lines.append("【跨题材轮换观察】煤炭、工业有色、宽基和传媒与589720同窗比较；不是同一行业的替代品。")
    if cross["leader"]:
        code = cross["leader"]
        cross_net = cross.get("compared_net", {}).get(code, 0)
        lines.append(f"跨题材领先：{cross['leader_theme']} {NAMES.get(code, code)} "
                     f"{cross['leader_cycles']}次，净差价约{cross_net}元，"
                     f"589720 {cross['baseline']}次；"
                     f"同一候选连续领先{cross['consecutive_weeks']}周。")
        if cross["switch_review_due"]:
            lines.append("跨题材触发人工复核：先核对现金占用、净差价、单边下跌库存损失、流动性及与159363的相关性；不是买单。")
        else:
            lines.append("跨题材未达到连续两周门槛；仅作观察。")
    else:
        lines.append("本周跨题材候选无一超过589720，允许继续持有现金，不为凑成交次数而切换。")
    if cross["missing"]:
        lines.append("跨题材数据缺失：" + "、".join(NAMES.get(code, code) for code in cross["missing"]))
    if errors:
        lines.append("数据缺失/失败：" + "、".join(errors))
    lines.append("模拟使用收盘价多槽位模型（含T+1、4槽并行、每格5000元），非5分钟成交回测或真实成交；"
                 "绝对数字偏乐观，相对排序可信。159992→589720的既定迁移不因本筛选自动暂停；"
                 "不自动买入、不自动撤单、不改变账户10万元和现金底线。")
    return "\n".join(lines)


if __name__ == "__main__":
    print(main())
