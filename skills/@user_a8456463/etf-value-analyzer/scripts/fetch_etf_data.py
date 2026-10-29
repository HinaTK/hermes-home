#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fetch_etf_data.py — ETF 投资价值评估器一键取数脚本（yfinance + AkShare 双引擎）

依赖：
    pip install yfinance akshare pandas

用法：
    # A股ETF
    python fetch_etf_data.py --symbol 510300 --market A
    python fetch_etf_data.py --symbol 159915 --market A

    # 港股ETF
    python fetch_etf_data.py --symbol 2800.HK --market HK

    # 美股ETF
    python fetch_etf_data.py --symbol SPY --market US

    # QDII ETF（需指定底层指数）
    python fetch_etf_data.py --symbol 513100 --market QDII --underlying "^NDX"

    # 自定义输出路径
    python fetch_etf_data.py --symbol 510300 --market A --output ./account/_temp_510300.json

设计原则（详见 references/api-data-source-protocol.md）：
- A股ETF 优先使用 AkShare；港股/美股ETF 优先使用 yfinance
- QDII ETF 双线并行：AkShare（场内）+ yfinance（底层指数）
- 所有失败信息记录到 errors[] 字段，但不中断主流程
- 输出标准 JSON 供 Skill 报告引用
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Windows 控制台 GBK 兼容
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _safe_get(d: Any, key: str, default: Any = None) -> Any:
    """安全取字典字段，避免 None 报错。"""
    if d is None:
        return default
    try:
        v = d.get(key, default) if isinstance(d, dict) else default
        if v is None or (isinstance(v, float) and (v != v)):  # NaN
            return default
        return v
    except Exception:
        return default


def _safe_float(val: Any, default: Any = None) -> Any:
    """安全转 float。"""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# yfinance 引擎 — ETF 版
# ---------------------------------------------------------------------------
def fetch_etf_via_yfinance(symbol: str) -> Dict[str, Any]:
    """通过 yfinance 取 ETF 数据（适用港股 / 美股 / A股交叉验证）。"""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    info = {}
    try:
        info = ticker.info or {}
    except Exception as e:
        raise RuntimeError(f"yfinance.info 调用失败: {e}")

    # fast_info 补充
    fast: Dict[str, Any] = {}
    try:
        fi = ticker.fast_info
        if fi is not None:
            for k in ("last_price", "previous_close", "year_high", "year_low",
                      "market_cap", "currency", "shares"):
                try:
                    fast[k] = getattr(fi, k, None)
                except Exception:
                    pass
    except Exception:
        pass

    price_current = _safe_get(info, "regularMarketPrice") or fast.get("last_price")
    previous_close = _safe_get(info, "regularMarketPreviousClose") or fast.get("previous_close")

    result: Dict[str, Any] = {
        "price": {
            "current": price_current,
            "currency": _safe_get(info, "currency") or fast.get("currency"),
            "previous_close": previous_close,
            "fifty_two_week_high": _safe_get(info, "fiftyTwoWeekHigh") or fast.get("year_high"),
            "fifty_two_week_low": _safe_get(info, "fiftyTwoWeekLow") or fast.get("year_low"),
            "data_type": "regular_market_price",
            "source": "yfinance",
        },
        "nav": {
            "unit_nav": _safe_get(info, "navPrice"),
            "source": "yfinance",
        },
        "fund_info": {
            "long_name": _safe_get(info, "longName"),
            "short_name": _safe_get(info, "shortName"),
            "fund_family": _safe_get(info, "fundFamily"),
            "category": _safe_get(info, "category"),
            "total_assets": _safe_get(info, "totalAssets"),
            "yield": _safe_get(info, "yield"),
            "expense_ratio": _safe_get(info, "annualReportExpenseRatio"),
            "beta_3y": _safe_get(info, "beta3Year"),
            "inception_date": _safe_get(info, "fundInceptionDate"),
            "source": "yfinance",
        },
        "performance": {
            "ytd_return": _safe_get(info, "ytdReturn"),
            "three_year_avg_return": _safe_get(info, "threeYearAverageReturn"),
            "five_year_avg_return": _safe_get(info, "fiveYearAverageReturn"),
            "source": "yfinance",
        },
        "valuation": {
            "trailing_pe": _safe_get(info, "trailingPE"),
            "forward_pe": _safe_get(info, "forwardPE"),
            "price_to_book": _safe_get(info, "priceToBook"),
            "source": "yfinance",
        },
    }

    # 尝试获取历史行情（用于计算波动率等）
    try:
        hist = ticker.history(period="3y")
        if hist is not None and not hist.empty:
            closes = hist["Close"].dropna()
            if len(closes) > 20:
                # 计算年化波动率
                daily_returns = closes.pct_change().dropna()
                vol_annual = float(daily_returns.std() * (250 ** 0.5)) if len(daily_returns) > 1 else None

                # 计算最大回撤
                peak = closes.expanding().max()
                drawdown = (closes - peak) / peak
                max_dd = float(drawdown.min()) if len(drawdown) > 0 else None

                # 年化收益率
                if len(closes) >= 250:
                    total_return = float(closes.iloc[-1] / closes.iloc[0] - 1)
                    years = len(closes) / 250
                    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else None
                else:
                    annual_return = None

                result["performance_calc"] = {
                    "volatility_annual": round(vol_annual * 100, 2) if vol_annual else None,
                    "max_drawdown_pct": round(max_dd * 100, 2) if max_dd else None,
                    "annual_return_pct": round(annual_return * 100, 2) if annual_return else None,
                    "sharpe_ratio": round(annual_return / vol_annual, 2) if (annual_return and vol_annual and vol_annual > 0) else None,
                    "data_period_days": len(closes),
                    "source": "yfinance(calculated)",
                }
    except Exception as e:
        result["performance_calc"] = {"_error": f"历史行情计算失败: {e}"}

    return result


# ---------------------------------------------------------------------------
# AkShare 引擎 — A 股 ETF
# ---------------------------------------------------------------------------
def fetch_etf_via_akshare_a(symbol: str) -> Dict[str, Any]:
    """通过 AkShare 取 A 股 ETF 数据。symbol 为纯 6 位代码，如 510300。"""
    import akshare as ak
    import pandas as pd

    errors: List[str] = []

    # 1. ETF 实时行情
    spot: Dict[str, Any] = {}
    try:
        df_spot = ak.fund_etf_spot_em()
        if df_spot is not None and not df_spot.empty:
            row = df_spot[df_spot["代码"] == symbol]
            if not row.empty:
                r = row.iloc[0].to_dict()
                spot = {
                    "current": _safe_float(r.get("最新价")),
                    "previous_close": _safe_float(r.get("昨收")),
                    "change_pct": _safe_float(r.get("涨跌幅")),
                    "volume": _safe_float(r.get("成交量")),
                    "turnover": _safe_float(r.get("成交额")),
                    "name": r.get("名称"),
                }
    except Exception as e:
        errors.append(f"fund_etf_spot_em 失败: {e}")

    # 2. ETF 基金信息
    fund_info: Dict[str, Any] = {}
    try:
        df_info = ak.fund_etf_fund_info_em()
        if df_info is not None and not df_info.empty:
            row = df_info[df_info["基金代码"] == symbol]
            if not row.empty:
                r = row.iloc[0].to_dict()
                fund_info = {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in r.items()}
    except Exception as e:
        errors.append(f"fund_etf_fund_info_em 失败: {e}")

    # 3. 历史行情（用于计算波动率/回撤）
    perf_calc: Dict[str, Any] = {}
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")
        df_hist = ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        if df_hist is not None and not df_hist.empty:
            closes = pd.to_numeric(df_hist["收盘"], errors="coerce").dropna()
            if len(closes) > 20:
                daily_returns = closes.pct_change().dropna()
                vol = float(daily_returns.std() * (250 ** 0.5))
                peak = closes.expanding().max()
                dd = (closes - peak) / peak
                max_dd = float(dd.min())
                total_ret = float(closes.iloc[-1] / closes.iloc[0] - 1)
                years = len(closes) / 250
                ann_ret = (1 + total_ret) ** (1 / years) - 1 if years > 0 else None

                perf_calc = {
                    "volatility_annual": round(vol * 100, 2),
                    "max_drawdown_pct": round(max_dd * 100, 2),
                    "annual_return_pct": round(ann_ret * 100, 2) if ann_ret else None,
                    "sharpe_ratio": round(ann_ret / vol, 2) if (ann_ret and vol > 0) else None,
                    "data_period_days": len(closes),
                    "source": "akshare(calculated)",
                }

                # 计算日均成交额（近20日）
                if "成交额" in df_hist.columns:
                    turnover = pd.to_numeric(df_hist["成交额"], errors="coerce").dropna()
                    if len(turnover) >= 20:
                        perf_calc["avg_daily_turnover_20d"] = round(float(turnover.tail(20).mean()), 2)
    except Exception as e:
        errors.append(f"fund_etf_hist_em 或绩效计算失败: {e}")

    # 4. 基金持仓（最新可用年份）
    holdings: Dict[str, Any] = {}
    try:
        current_year = datetime.now().year
        for year in [str(current_year), str(current_year - 1)]:
            try:
                df_hold = ak.fund_portfolio_hold_em(symbol=symbol, date=year)
                if df_hold is not None and not df_hold.empty:
                    top_10 = []
                    for i, row in df_hold.head(10).iterrows():
                        item = {}
                        for col in df_hold.columns:
                            item[col] = row[col]
                        top_10.append(item)
                    holdings = {
                        "top_10": top_10,
                        "total_count": len(df_hold),
                        "report_year": year,
                        "source": "akshare",
                    }
                    break
            except Exception:
                continue
    except Exception as e:
        errors.append(f"fund_portfolio_hold_em 失败: {e}")

    result = {
        "price": {
            "current": spot.get("current"),
            "currency": "CNY",
            "previous_close": spot.get("previous_close"),
            "change_pct": spot.get("change_pct"),
            "volume": spot.get("volume"),
            "turnover": spot.get("turnover"),
            "data_type": "regular_market_close",
            "source": "akshare",
        },
        "fund_info": {
            "name": spot.get("name"),
            **fund_info,
            "source": "akshare",
        },
        "holdings": holdings,
        "performance_calc": perf_calc,
        "_errors_partial": errors,
    }
    return result


# ---------------------------------------------------------------------------
# AkShare 引擎 — 指数估值
# ---------------------------------------------------------------------------
def fetch_index_valuation(index_name: str) -> Dict[str, Any]:
    """通过 AkShare 获取指数估值历史（PE/PB/股息率分位）。"""
    import akshare as ak

    result: Dict[str, Any] = {}
    errors: List[str] = []

    for indicator in ["市盈率", "市净率"]:
        try:
            df = ak.index_value_hist_funddb(symbol=index_name, indicator=indicator)
            if df is not None and not df.empty:
                latest = df.iloc[-1].to_dict()
                key = "pe" if "盈" in indicator else "pb"
                result[key] = {
                    str(k): (str(v) if hasattr(v, "isoformat") else v)
                    for k, v in latest.items()
                }
        except Exception as e:
            errors.append(f"index_value_hist_funddb({index_name}, {indicator}) 失败: {e}")

    result["source"] = "akshare/funddb"
    if errors:
        result["_errors"] = errors
    return result


# ---------------------------------------------------------------------------
# 编排
# ---------------------------------------------------------------------------
def normalize_etf_symbol(symbol: str, market: str) -> Dict[str, str]:
    """根据 market 标准化 ETF 代码。"""
    s = symbol.strip()
    market = market.upper()

    if market == "A" or market == "QDII":
        num = s.zfill(6)
        if num.startswith(("51", "56", "58", "15", "16")):
            # 51/56/58 上交所, 15/16 深交所
            if num.startswith(("51", "56", "58")):
                yf_sym = f"{num}.SS"
            else:
                yf_sym = f"{num}.SZ"
        else:
            yf_sym = f"{num}.SS"
        return {"akshare": num, "yfinance": yf_sym}

    if market == "HK":
        if s.upper().endswith(".HK"):
            yf_sym = s.upper()
            num = s.upper().replace(".HK", "").lstrip("0")
            ak_sym = f"{int(num):05d}"
        else:
            num = s.lstrip("0") or "0"
            yf_sym = f"{int(num):04d}.HK"
            ak_sym = f"{int(num):05d}"
        return {"yfinance": yf_sym, "akshare": ak_sym}

    # US
    return {"yfinance": s.upper(), "akshare": s.upper()}


def detect_etf_type(symbol: str, market: str, info: Dict[str, Any]) -> str:
    """根据已获取信息判断 ETF 类型。"""
    market = market.upper()
    if market == "QDII":
        return "qdii"

    name = str(info.get("fund_info", {}).get("name", "") or
               info.get("fund_info", {}).get("long_name", "") or "")
    category = str(info.get("fund_info", {}).get("category", "") or "")

    # 商品 ETF 关键词
    commodity_keywords = ["黄金", "白银", "原油", "豆粕", "能源化工", "有色金属",
                          "Gold", "Silver", "Oil", "Commodity"]
    for kw in commodity_keywords:
        if kw in name or kw in category:
            return "commodity"

    # QDII 关键词
    qdii_keywords = ["QDII", "纳指", "标普", "恒生", "纳斯达克", "日经", "法国", "德国", "越南"]
    for kw in qdii_keywords:
        if kw in name:
            return "qdii"

    # 行业/主题 ETF 关键词
    sector_keywords = ["半导体", "芯片", "新能源", "光伏", "消费", "医药", "医疗", "银行",
                       "证券", "军工", "房地产", "科技", "互联网", "汽车", "钢铁", "煤炭",
                       "食品", "饮料", "农业", "建材", "化工", "电力", "通信",
                       "Technology", "Financial", "Health", "Energy", "Semiconductor"]
    for kw in sector_keywords:
        if kw in name or kw in category:
            return "sector"

    return "broad_index"


def fetch_all(symbol: str, market: str, underlying: Optional[str] = None) -> Dict[str, Any]:
    """ETF 数据聚合。"""
    norm = normalize_etf_symbol(symbol, market)
    engines_used: List[str] = []
    engines_failed: List[Dict[str, str]] = []
    errors: List[str] = []
    merged: Dict[str, Any] = {}

    market_upper = market.upper()

    # ---- A 股 ETF / QDII ----
    if market_upper in ("A", "QDII"):
        # AkShare 主取
        try:
            data = fetch_etf_via_akshare_a(norm["akshare"])
            merged.update(data)
            engines_used.append("akshare")
            if data.get("_errors_partial"):
                errors.extend(data.pop("_errors_partial"))
        except Exception as e:
            engines_failed.append({"engine": "akshare", "error": str(e)})
            errors.append(f"akshare: {e}")

        # yfinance 交叉验证
        try:
            data_yf = fetch_etf_via_yfinance(norm["yfinance"])
            merged["_yfinance_cross_check"] = data_yf
            engines_used.append("yfinance(cross-check)")
        except Exception as e:
            engines_failed.append({"engine": "yfinance(cross-check)", "error": str(e)})

        # QDII: 获取底层指数数据
        if market_upper == "QDII" and underlying:
            try:
                data_underlying = fetch_etf_via_yfinance(underlying)
                merged["underlying_index"] = data_underlying
                engines_used.append(f"yfinance(underlying:{underlying})")
            except Exception as e:
                engines_failed.append({"engine": f"yfinance(underlying:{underlying})", "error": str(e)})
                errors.append(f"底层指数取数失败: {e}")

    # ---- 港股 / 美股 ETF ----
    elif market_upper in ("HK", "US"):
        try:
            data = fetch_etf_via_yfinance(norm["yfinance"])
            merged.update(data)
            engines_used.append("yfinance")
        except Exception as e:
            engines_failed.append({"engine": "yfinance", "error": str(e)})
            errors.append(f"yfinance: {e}")

    else:
        errors.append(f"未知市场类型: {market}（仅支持 A/HK/US/QDII）")

    # 自动检测 ETF 类型
    etf_type = detect_etf_type(symbol, market, merged)

    return {
        "meta": {
            "symbol_input": symbol,
            "market": market_upper,
            "etf_type": etf_type,
            "etf_type_cn": {
                "broad_index": "宽基指数",
                "sector": "行业/主题",
                "qdii": "跨境QDII",
                "commodity": "商品",
            }.get(etf_type, "未知"),
            "underlying_index": underlying,
            "symbol_normalized": norm,
            "fetch_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetch_time_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engines_used": engines_used,
            "engines_failed": engines_failed,
        },
        **merged,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ETF 投资价值评估器一键取数脚本（yfinance + AkShare 双引擎）"
    )
    parser.add_argument("--symbol", required=True,
                        help="ETF代码，如 510300 / 2800.HK / SPY / 513100")
    parser.add_argument("--market", required=True,
                        choices=["A", "HK", "US", "QDII", "a", "hk", "us", "qdii"],
                        help="市场类型：A（A股）/ HK（港股）/ US（美股）/ QDII（跨境）")
    parser.add_argument("--underlying", default=None,
                        help="QDII ETF的底层指数代码，如 ^NDX（纳斯达克100）")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--print", action="store_true", help="同时打印到 stdout")

    args = parser.parse_args()

    try:
        data = fetch_all(args.symbol, args.market, args.underlying)
    except Exception as e:
        print(f"[ERROR] 取数过程发生未捕获异常: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    # 输出路径
    if args.output:
        output_path = args.output
    else:
        safe_sym = args.symbol.replace(".", "_").replace("/", "_").replace("^", "_")
        output_dir = "./account"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"_temp_etf_analysis_{safe_sym}.json")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # 输出摘要
    print(f"[OK] ETF 取数完成 -> {output_path}")
    print(f"     ETF类型: {data['meta']['etf_type_cn']}({data['meta']['etf_type']})")
    print(f"     使用引擎: {data['meta']['engines_used']}")
    if data["meta"]["engines_failed"]:
        print(f"     [WARN] 失败引擎: {data['meta']['engines_failed']}")
    price = data.get("price", {})
    if price.get("current"):
        print(f"     当前价格: {price['current']} {price.get('currency', '')}")
    fund = data.get("fund_info", {})
    if fund.get("total_assets"):
        try:
            assets_b = float(fund["total_assets"]) / 1e8
            print(f"     基金规模: {assets_b:.2f}亿")
        except Exception:
            pass
    if fund.get("expense_ratio"):
        try:
            print(f"     费率: {float(fund['expense_ratio']) * 100:.2f}%")
        except Exception:
            pass
    perf = data.get("performance_calc", {})
    if perf.get("volatility_annual"):
        print(f"     年化波动率: {perf['volatility_annual']}%")
    if perf.get("max_drawdown_pct"):
        print(f"     最大回撤: {perf['max_drawdown_pct']}%")

    if getattr(args, "print", False):
        print("\n--- JSON 内容 ---")
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
