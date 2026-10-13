# -*- coding: utf-8 -*-
"""
网格交易 筛选 + 计算器  (CLI, 手动执行版)
========================================
功能:
  1. 内置 T+0 交易的 ETF / LOF 池 (不含货币/债券型; 可在 UNIVERSE 增删, 或用 --universe 自定义 CSV)
  2. 按 "均线黏合 + 横盘震荡(>=1个月) + 有效箱体 + 排除下跌趋势/创新低" 四个条件筛选标的
  3. LOF 流动性门槛: 近5日均成交额过小的 LOF 直接剔除 (--min_amount, 默认2000万)
  4. 箱体识别(硬条件): 近80日内必须"至少两个高点能连成上轨 + 两个低点能连成下轨",
     且上下轨必须在近20日内仍有价格回到附近(旧箱体失效不算), 当前价仍在箱体之内;
     单点尖顶/尖底不算箱体, 已向上突破/向下跌破/ stale 旧箱体一律剔除;
     网格上/下界 = 箱体上/下轨的触及价位
  5. 网格间距 = 该ETF近1月日均波幅 ADR × 0.7(保底1%), 每只不同, 即你填入券商APP的"网格间距"
  6. 综合评分(0-100, 越高越适合做网格): 黏合好+波动小+振幅稳+价格居中+趋势平; 结果按评分降序, 前3只标★推荐
  7. 输出: 控制台摘要表 + grid_results.csv + grid_report.html (含价格/均线走势与网格线可视化,
     上界/下界/中枢(建议基准价)/网格间距四参数已标红加粗, 每只含综合评分·排名·溢价率·箱体触及次数)

数据源: 腾讯财经行情接口 (无需密钥, 适合本机手动跑)
依赖: 仅 Python 标准库 (urllib / json / statistics / csv / argparse / concurrent.futures)

用法示例:
  python grid_tool.py                      # 默认: 间距=日均波幅×0.7(保底1%), 通道=高/低价85/15分位, 价格须在区间内
  python grid_tool.py --step 1.5          # 固定网格间距为 1.5% (关闭自适应)
  python grid_tool.py --grids 12          # 固定网格档数为 12 档
  python grid_tool.py --box_window 100 --box_tol 1.5  # 箱体识别放宽: 看近100日, 高低点判定宽度1.5%
  python grid_tool.py --adr_mult 1.5      # 间距 = ADR×1.5 (整体放宽; 默认1.0=ADR×0.7保底1%口径, 非1.0时不足1%取1%)
  python grid_tool.py --adr_window 40     # ADR 改用近40日计算
  python grid_tool.py --capital 100000    # 投入 10 万, 给出每格金额
  python grid_tool.py --min_amount 3000000 --liquid_all   # 流动性门槛应用到全部标的
  python grid_tool.py --conv 8 --amp20 10 --amp40 15 --vol 35   # 放宽筛选
  python grid_tool.py --top 20            # 只展示综合评分最高的前 20 只
  python grid_tool.py --min_results 12    # 结果不足12只时自动逐级放宽阈值补齐(默认10, 评分低也保留)
  python grid_tool.py --no_fill           # 关闭数量兜底, 仅输出严格达标标的
  python grid_tool.py --bounds golden      # 黄金分割模式: 上界≈六一八线, 下界≈三八二线; 并用250日内多次触碰的压力/支撑位修正
  python grid_tool.py --bounds golden --gold_upper 0.809 --gold_lower 0.236  # 上界=八零九、下界=二三六, 区间更宽
"""

# 说明: 成交额由 "成交量(手) × 100 × VWAP" 估算(腾讯日K成交量单位为手, 1手=100股; 行情接口不直接给成交额), 用于流动性门槛,
#       量级准确、排序可靠, 标注为"估算"。

import argparse
import csv
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# ----------------------------------------------------------------------------
# 1. T+0 ETF / LOF 标的池 (可在下方增删; 货币ETF 默认排除, 因其近乎无波动不适合网格)
#    code: 6 位代码; name: 名称; kind: 类别(仅展示用)
# ----------------------------------------------------------------------------
UNIVERSE = [
    # ===== 黄金 ETF (T+0) =====
    ("518880", "黄金ETF华安", "黄金"), ("518800", "黄金ETF国泰", "黄金"),
    ("518850", "黄金ETF华夏", "黄金"), ("518660", "黄金ETF工银", "黄金"),
    ("159934", "黄金ETF易方达", "黄金"), ("159937", "黄金ETF博时", "黄金"),
    ("159812", "黄金ETF前海开源", "黄金"), ("518600", "金ETF广发", "黄金"),
    ("518680", "金ETF富国", "黄金"), ("159830", "金ETF天弘", "黄金"),
    ("159831", "金ETF嘉实", "黄金"), ("159834", "金ETF南方", "黄金"),
    ("518890", "上海金ETF中银", "黄金"),
    # ===== 商品期货 ETF (T+0) =====
    ("159980", "有色ETF大成", "商品"), ("159981", "能源化工ETF建信", "商品"),
    ("159985", "豆粕ETF华夏", "商品"),
    # ===== 跨境 ETF (T+0, QDII: 港股/美股/日欧/新兴) =====
    ("159329", "沙特ETF南方", "跨境"), ("159501", "纳指ETF嘉实", "跨境"),
    ("159502", "标普生物科技ETF嘉实", "跨境"), ("159509", "纳指科技ETF景顺", "跨境"),
    ("159518", "标普油气ETF嘉实", "跨境"), ("159605", "中概互联ETF广发", "跨境"),
    ("159612", "标普500ETF国泰", "跨境"), ("159632", "纳斯达克ETF华安", "跨境"),
    ("159636", "港股通科技30ETF工银", "跨境"), ("159655", "标普500ETF华夏", "跨境"),
    ("159659", "纳斯达克100ETF招商", "跨境"), ("159740", "恒生科技ETF大成", "跨境"),
    ("159741", "恒生科技ETF嘉实", "跨境"), ("159742", "恒生科技ETF博时", "跨境"),
    ("159792", "港股通互联网ETF富国", "跨境"), ("159866", "日经ETF工银", "跨境"),
    ("159920", "恒生ETF华夏", "跨境"), ("159941", "纳指ETF广发", "跨境"),
    ("159954", "恒生中国企业ETF南方", "跨境"), ("159960", "恒生中国企业ETF平安", "跨境"),
    ("510900", "恒生中国企业ETF易方达", "跨境"), ("513000", "日经225ETF易方达", "跨境"),
    ("513010", "恒生科技ETF易方达", "跨境"), ("513030", "德国ETF华安", "跨境"),
    ("513050", "中概互联网ETF易方达", "跨境"), ("513060", "恒生医疗ETF博时", "跨境"),
    ("513070", "港股通消费ETF易方达", "跨境"), ("513080", "法国ETF华安", "跨境"),
    ("513090", "香港证券ETF易方达", "跨境"), ("513100", "纳指ETF国泰", "跨境"),
    ("513110", "纳指ETF华泰柏瑞", "跨境"), ("513120", "港股创新药ETF广发", "跨境"),
    ("513130", "恒生科技ETF华泰柏瑞", "跨境"), ("513180", "恒生科技ETF华夏", "跨境"),
    ("513200", "港股通医药ETF易方达", "跨境"), ("513260", "恒生科技ETF汇添富", "跨境"),
    ("513290", "纳指生物科技ETF汇添富", "跨境"), ("513300", "纳斯达克ETF华夏", "跨境"),
    ("513310", "中韩半导体ETF华泰柏瑞", "跨境"), ("513320", "港股通新经济ETF易方达", "跨境"),
    ("513330", "恒生互联网ETF华夏", "跨境"), ("513380", "恒生科技ETF广发", "跨境"),
    ("513390", "纳指100ETF博时", "跨境"), ("513400", "道琼斯ETF鹏华", "跨境"),
    ("513500", "标普500ETF博时", "跨境"), ("513520", "日经ETF华夏", "跨境"),
    ("513550", "港股通50ETF华泰柏瑞", "跨境"), ("513580", "恒生科技ETF华安", "跨境"),
    ("513600", "恒生指数ETF南方", "跨境"), ("513630", "港股低波红利ETF摩根", "跨境"),
    ("513650", "标普500ETF南方", "跨境"), ("513660", "恒生ETF华夏", "跨境"),
    ("513700", "港股通医药ETF鹏华", "跨境"), ("513730", "东南亚科技ETF华泰柏瑞", "跨境"),
    ("513770", "港股互联网ETF华宝", "跨境"), ("513850", "美国50ETF易方达", "跨境"),
    ("513860", "港股通科技ETF海富通", "跨境"), ("513870", "纳指ETF富国", "跨境"),
    ("513880", "日经225ETF华安", "跨境"), ("513890", "恒生科技ETF摩根", "跨境"),
    ("513900", "港股通100ETF华安", "跨境"), ("513970", "恒生消费ETF景顺", "跨境"),
    ("520570", "恒生科技ETF南方", "跨境"),
    # ===== 跨境 LOF (T+0, QDII) =====
    ("160140", "美国REIT精选LOF", "LOF"), ("160216", "国泰商品LOF", "LOF"),
    ("160416", "石油基金LOF", "LOF"), ("160719", "嘉实黄金LOF", "LOF"),
    ("161116", "黄金主题LOF", "LOF"), ("161125", "标普500LOF", "LOF"),
    ("161128", "标普信息科技LOF", "LOF"), ("161130", "纳斯达克100LOF", "LOF"),
    ("161226", "国投白银LOF", "LOF"), ("161815", "抗通胀LOF", "LOF"),
    ("162411", "华宝油气LOF", "LOF"), ("162415", "美国消费LOF", "LOF"),
    ("162719", "石油LOF", "LOF"), ("163208", "全球油气能源LOF", "LOF"),
    ("164701", "黄金LOF", "LOF"), ("164824", "印度基金LOF", "LOF"),
    ("501018", "南方原油LOF", "LOF"),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ---- 箱体识别参数 ----
BOX_SPAN = 2                # 摆动点判定: 左右各看几根K线
BOX_TOL_MAX = 3.0           # 聚簇容差上限%% (超过该值仍找不到箱体即判定无箱体)


def market_prefix(code: str) -> str:
    """上交所 5/6 开头 -> sh; 其余(0/1/2/3 开头) -> sz"""
    return "sh" if code[0] in "56" else "sz"


def fetch_kline(code: str, datalen: int = 500):
    """从腾讯财经取日 K (前复权), 返回 (dates, opens, closes, highs, lows) 或 None"""
    symbol = market_prefix(code) + code
    url = (f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
           f"?param={symbol},day,,,{datalen},qfq")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        j = json.loads(raw)
        node = j.get("data", {}).get(symbol)
        if not node:
            return None
        bars = node.get("qfqday") or node.get("day")
        if not bars:
            return None
        dates, opens, closes, highs, lows, vols = [], [], [], [], [], []
        for b in bars:  # [date, open, close, high, low, volume]
            dates.append(b[0]); opens.append(float(b[1])); closes.append(float(b[2]))
            highs.append(float(b[3])); lows.append(float(b[4])); vols.append(float(b[5]))
        return dates, opens, closes, highs, lows, vols
    except Exception:
        return None


def fetch_nav(code: str):
    """东财基金净值接口, 取最新单位净值(DWJZ)与净值日期; 用于计算 ETF 溢价率。
       返回 (nav, nav_date) 或 (None, None)。跨境ETF净值可能滞后1-2日, 溢价率为估算口径。"""
    url = (f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}"
           f"&pageIndex=1&pageSize=1&_=1")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Referer": "http://fundf10.eastmoney.com/"})
        raw = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
        d = json.loads(raw)
        lst = (d.get("Data") or {}).get("LSJZList") or []
        if not lst:
            return None, None
        row = lst[0]
        return float(row.get("DWJZ")), row.get("FSRQ")
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# 回测引擎(固定手数、当日扫线模型)
# ---------------------------------------------------------------------------
def swing_extrema(highs, lows, span=BOX_SPAN):
    """识别摆动高/低点(局部极值): 某根K线的最高价是前后 span 根内最高 -> 摆动高点。
       返回 (高点索引列表, 低点索引列表)。"""
    n = len(highs)
    sh, sl = [], []
    for i in range(span, n - span):
        if highs[i] >= max(highs[i - span:i + span + 1]) - 1e-12:
            sh.append(i)
        if lows[i] <= min(lows[i - span:i + span + 1]) + 1e-12:
            sl.append(i)
    return sh, sl


def cluster_best(pairs, tol_pct, want_max, edge_min_members=2):
    """把价格接近的摆动点连成"连续串"作为候选水平线（同时用于上轨和下轨）。
    先按价格排序, 相邻两点差异<=tol_pct 就连成一串; 每个串成员>=2 只是一簇, 但还要满足
    "edge 水平至少有 edge_min_members 个真正的触及点", 才算"两个高/低点水平相连"。
    want_max=True 时, edge = 串内最高价 —— 用于上轨留足卖出空间、降低卖飞;
                         也用于下轨: 取串内最高价作为保守托底线(避免近期最低点把下界拉得太低)。
    want_max=False 时, edge = 串内最低价。
    多个候选时, 取 edge 更高的; 有近期成员的簇优先(通过 identify_box 外层校验)。"""
    if len(pairs) < 2:
        return None, None, []
    s = sorted(pairs, key=lambda p: p[1])
    n = len(s)
    best = None
    best_score = None
    half = tol_pct / 2.0 / 100.0  # edge 水平附近容差
    i = 0
    while i < n:
        j = i + 1
        while j < n and abs(s[j][1] / s[j - 1][1] - 1) * 100.0 <= tol_pct:
            j += 1
        members = s[i:j]
        if len(members) >= 2:
            edge = max(p[1] for p in members) if want_max else min(p[1] for p in members)
            # edge 水平附近(±tol/2)必须至少有 edge_min_members 个真正的摆动点
            if want_max:
                edge_members = [p for p in members if p[1] >= edge * (1 - half)]
            else:
                edge_members = [p for p in members if p[1] <= edge * (1 + half)]
            if len(edge_members) >= edge_min_members:
                center = sum(p[1] for p in members) / len(members)
                score = (-edge, -len(members)) if want_max else (edge, -len(members))
                if best is None or score < best_score:
                    best = (edge, center, [p[0] for p in members])
                    best_score = score
        i = j
    return best if best else (None, None, [])


def alternations(hi_idx, lo_idx):
    """把上轨/下轨的触及点按时间排序, 统计"高<->低"的交替次数。
       交替多 = 价格在上下轨之间来回震荡(真箱体);
       〉例: 低 高 低 高 -> 3 次(真箱体); 低 低 高 高 -> 1 次(单边上涨后高位横盘, 不是箱体)。
       返回交替次数。"""
    seq = sorted([(i, 1) for i in hi_idx] + [(i, 0) for i in lo_idx])
    if len(seq) < 3:
        return 0
    return sum(1 for k in range(1, len(seq)) if seq[k][1] != seq[k - 1][1])


def identify_box(highs, lows, window, tol_start, tol_max=BOX_TOL_MAX, span_ratio=0.35,
                 min_alternations=3, lower_rail_stale=40):
    """箱体识别: 在近 window 日中找"至少两个高点可连成上轨 + 两个低点可连成下轨"的震荡区间。
       上轨和下轨都用"价格连续串": 把价格接近的摆动高点/低点连成水平线, 要求每个串至少2个点,
       且 edge 水平(±tol/2)上也至少2个真正的触及点, 避免"只有一个点在水平线上、其余都更低/更高"的假箱体。
       上轨 edge = 串内最高价(箱体里最高的那个高点, 留足卖出空间, 降低卖飞);
       下轨 edge = 串内最高价(两个能水平相连的低点里最高的那条支撑线, 保守托底, 避免用孤立最低点把下界拉太低)。
       容差上限 = min(tol_max, 窗口整体振幅 × span_ratio) —— 若容差接近或超过箱体高度,
       所有高/低点都会被归进同一串, 那样等于没有箱体约束(单调上行也会被误判成箱体),
       因此容差必须相对箱体高度收紧。容差从 tol_start 起逐步放宽到上限, 仍找不到即判定无箱体。
       返回 (upper, lower, n_hi, n_lo, used_tol, span_days, hi_idx, lo_idx);
       无箱体则返回 (None, None, 0, 0, None, 0, [], [])。
       span_days = 首次触及到最后触及之间跨越的交易日数(衡量箱体震荡了多久)。
       hi_idx / lo_idx 是聚簇成员在窗口内的索引, 供调用方分别统计"真正触线次数"。"""
    hs = highs[-window:]; ls = lows[-window:]
    sh, sl = swing_extrema(hs, ls)
    hi_pairs = [(i, hs[i]) for i in sh]
    lo_pairs = [(i, ls[i]) for i in sl]
    if len(hi_pairs) < 2 or len(lo_pairs) < 2:
        return None, None, 0, 0, None, 0, [], []

    lo_base = min(ls)
    if lo_base <= 0:
        return None, None, 0, 0, None, 0, [], []
    span_pct = (max(hs) - lo_base) / lo_base * 100.0
    tol_cap = min(tol_max, span_pct * span_ratio)
    if tol_cap <= 0:
        return None, None, 0, 0, None, 0, [], []

    tol = min(tol_start, tol_cap)
    while tol <= tol_cap + 1e-9:
        upper, _, hi_idx = cluster_best(hi_pairs, tol, want_max=True, edge_min_members=2)
        lower, _, lo_idx = cluster_best(lo_pairs, tol, want_max=True, edge_min_members=2)
        if upper is not None and lower is not None and upper > lower * 1.01:
            # 时间上必须来回交错: 低-高-低-高 才是箱体; 低低高高(单边后横盘)不算
            if alternations(hi_idx, lo_idx) >= min_alternations:
                seq = sorted(hi_idx + lo_idx)
                return upper, lower, len(hi_idx), len(lo_idx), tol, seq[-1] - seq[0], hi_idx, lo_idx
        tol += 0.25
    return None, None, 0, 0, None, 0, [], []


def golden_top_bottom(highs, lows, window, lag):
    """黄金分割区间(仿通达信主力黄金线公式):
       取近 window 日(不含最近 lag 日, 即 REF(HHV(HIGH,window),lag)) 的最高价作"顶"、
       最低价作"零"; 返回 (top, bottom, lines), lines 为 7 条黄金分割参考价:
       0.0(零) 0.236 0.382 0.5(中) 0.618 0.809 1.0(顶)。"""
    need = window + lag
    seg_h = highs[-need:] if len(highs) >= need else highs
    seg_l = lows[-need:] if len(lows) >= need else lows
    top = max(seg_h[:-lag]) if (lag > 0 and len(seg_h) > lag) else max(seg_h)
    bottom = min(seg_l[:-lag]) if (lag > 0 and len(seg_l) > lag) else min(seg_l)
    if bottom <= 0:
        return top, bottom, []
    lines = [bottom + (top - bottom) * f for f in (0.0, 0.236, 0.382, 0.5, 0.618, 0.809, 1.0)]
    return top, bottom, lines


def _hist_peaks(prices, bin_frac, min_touches, gap_bins=2):
    """把一组价格做成分布直方图, 返回"局部峰值价"(众数附近)列表及其出现次数, 按价格升序。
       价格反复落在同一价位附近会在直方图上形成一个"峰", 峰顶价就是那条"多次触碰"的水平线。
       - bin_frac: 分档宽度(相对价格), 默认 0.4% —— 足够分辨相隔 1% 以上的两条线。
       - min_touches: 一个价位至少被触碰这么多次才承认是"有效水平线"(默认3次)。
       - gap_bins: 局部最大需压过左右各几个分档(默认2), 避免把同一坡上的相邻分档都当成"峰"。
       返回 [(峰值均价, 触碰次数), ...]。"""
    if not prices:
        return []
    base = min(prices)
    binw = max(base * bin_frac, 1e-9)
    bins = {}
    for p in prices:
        b = round(p / binw)
        bins[b] = bins.get(b, 0) + 1
    keys = sorted(bins)
    peaks = []
    for k in keys:
        cnt = bins[k]
        if cnt < min_touches:
            continue
        is_peak = True
        for d in range(1, gap_bins + 1):
            for nb in (k - d, k + d):
                if nb in bins and bins[nb] > cnt:
                    is_peak = False
                    break
            if not is_peak:
                break
        if is_peak:
            members = [p for p in prices if round(p / binw) == k]
            peaks.append((sum(members) / len(members), cnt))
    return peaks


def pressure_support_levels(highs, lows, window, bin_frac=0.004, min_touches=3):
    """在较长窗口内识别"多次触碰的压力位/支撑位"(直方图峰值法)。
       用窗口内所有日K的最高价(找压力位)和最低价(找支撑位)分别做分布直方图,
       取局部峰值价——价格反复落在同一价位附近会形成峰, 这就是"多次触碰"的水平线。
       返回 (pressures, supports):
       - pressures: (价格, 触碰次数) 列表, 当前价上方, 按价格从高到低排序
       - supports:  (价格, 触碰次数) 列表, 当前价下方, 按价格从低到高排序
       相比只用摆动极值, 这里用"所有日K高低点"做直方图, 因为"价格摸到某条线"
       不需要是严格的局部高/低点, 只要当天最高/最低接近即可。"""
    hi_prices = highs[-window:] if len(highs) >= window else highs
    lo_prices = lows[-window:] if len(lows) >= window else lows
    cur = (highs[-1] + lows[-1]) / 2.0

    pressures = [p for p in _hist_peaks(hi_prices, bin_frac, min_touches) if p[0] > cur]
    supports = [s for s in _hist_peaks(lo_prices, bin_frac, min_touches) if s[0] < cur]
    pressures.sort(key=lambda x: x[0], reverse=True)
    supports.sort(key=lambda x: x[0])
    return pressures, supports


def ma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def pct(vals, p):
    """百分位数 (线性插值), p 为 0-100"""
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def evaluate(code, name, kind, kline, args):
    """计算全部指标并返回 (candidate_dict, None) 或 (None, 失败原因)。
       candidate_dict 含所有指标与综合评分(评分用基准阈值计算, 作为稳定的质量度量),
       但不含 NAV/溢价率 —— 选中后再取, 避免未入选标的浪费接口调用。
       紧凑度/振幅/波动/趋势/箱体/流动性 等"质量"过滤不在本函数硬性剔除,
       交由 main() 的兜底放宽循环(relax_select)判定, 这样无论放宽到哪一档都有评分可排序。
       仅"硬安全过滤"(无行情/数据不足/通道异常)在此返回 (None, 原因)。"""
    if not kline:
        return None, "无行情数据"
    dates, opens, closes, highs, lows, vols = kline
    if len(closes) < 60:
        return None, "数据不足(<60日)"

    ma5, ma10, ma20, ma60 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 60)
    mas = [ma5, ma10, ma20, ma60]
    conv = (max(mas) - min(mas)) / sum(mas) * len(mas) * 100.0  # 均线黏合度(%)

    # 横盘震荡: 看近 20 日(约1个月)与近 40 日(约2个月)振幅
    h20, l20 = max(highs[-20:]), min(lows[-20:])
    h40, l40 = max(highs[-40:]), min(lows[-40:])
    m20 = sum(closes[-20:]) / 20
    m40 = sum(closes[-40:]) / 40
    amp20 = (h20 - l20) / m20 * 100.0
    amp40 = (h40 - l40) / m40 * 100.0

    # 年化波动率(近 60 日)
    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 59, len(closes))]
    ann_vol = statistics.pstdev(rets) * math.sqrt(252) * 100.0

    cur = closes[-1]
    prev = closes[-2]
    chg = (cur / prev - 1) * 100.0

    # 近5日估算成交额 (成交量(手) × 100 × VWAP, 1手=100股), 用于 LOF 流动性门槛
    est_amt = [vols[i] * 100 * ((closes[i] + highs[i] + lows[i]) / 3)
               for i in range(len(closes) - 5, len(closes))]
    amount_5d = statistics.mean(est_amt)
    amount_1d = est_amt[-1]  # 前一日(最近一交易日)估算成交额, 用于单日流动性硬门槛

    # ---- 区间(上/下界)确定: 箱体模式 或 黄金分割模式 ----
    box_days = 0
    used_tol = 0.0
    n_hi = n_lo = 0
    touch_hi = touch_lo = 0
    gold_top = gold_bottom = 0.0
    gold_lines = []
    is_golden = (args.bounds == "golden")
    if is_golden:
        gtop, gbot, glines = golden_top_bottom(highs, lows, args.gold_window, args.gold_lag)
        if gbot <= 0:
            return None, "黄金分割区间异常(最低价非正)"
        gold_top, gold_bottom, gold_lines = gtop, gbot, glines
        upper_box = gtop - (gtop - gbot) * (1.0 - args.gold_upper)
        lower = gbot + (gtop - gbot) * args.gold_lower
        box_high, box_low = gtop, gbot
        # ---- 压力位/支撑位修正: 在更长窗口内找出"多次触碰"的真实高/低点(水平线),
        #     把黄金分割上界/下界都向这些真实水平线收敛, 使网格边界贴合人眼可见的前期反复触碰位置。
        #     上界(卖出线)修正: 只有当现价贴近上界(正在挑战压力)时才上修, 卖飞线保持保守;
        #     下界(买点)修正: 默认以 0.382 线为锚; 若 0.236 线附近有强支撑, 则把下界锚到该强支撑,
        #     避免机械下界过深导致跌破后深套, 同时保留向更深支撑位下修的能力。 ----
        pressures, supports = pressure_support_levels(
            highs, lows, args.gold_pressure_window,
            bin_frac=args.gold_bin_frac, min_touches=args.gold_min_touches)
        # 上界: 现价贴近上界时, 上修到最近的、差距在 [min_gap, tol] 内的压力位
        if pressures and cur >= upper_box * (1.0 - args.gold_correct_near / 100.0):
            for p, _cnt in pressures:  # pressures 从高到低, 取最接近 upper_box 的(最小的那个够格的)
                gap = (p / upper_box - 1) * 100.0
                if args.gold_pressure_min_gap <= gap <= args.gold_pressure_tol:
                    upper_box = p
                    break
        # 下界: 先以 0.382 线为基准
        lower = gbot + (gtop - gbot) * args.gold_lower
        used_236 = False
        # 如果 0.236 线附近有强支撑(触碰次数>=8), 优先把下界锚到该强支撑(更贴合前期低点),
        # 选离 0.236 线最近的那一个, 且必须不高于 0.382 线, 避免被近期震荡区(更高次)拉偏。
        l236 = gbot + (gtop - gbot) * 0.236
        l382 = lower  # 当前 0.382 线
        best_236, best_236_gap = None, 1e18
        for s, cnt in supports:
            if s > l382 * 1.005:
                continue
            gap = abs(s / l236 - 1) * 100.0
            if gap <= args.gold_pressure_tol and cnt >= 8:
                if gap < best_236_gap:
                    best_236_gap = gap
                    best_236 = s
        if best_236 is not None:
            lower = best_236
            used_236 = True
        # 只有在没有使用 0.236 强支撑时才继续向下修正: 找[gold_correct_near, tol]范围内的更深支撑
        if not used_236:
            for s, cnt in supports:
                if s >= lower:
                    continue
                gap = (lower / s - 1) * 100.0
                if args.gold_correct_near <= gap <= args.gold_pressure_tol:
                    lower = s
                    break
        if cur > upper_box * 1.002:
            return None, "价格已突破黄金分割区间上沿"
        if cur < lower * 0.998:
            return None, "价格已跌破黄金分割区间下沿"
    if not is_golden:
        box_high = max(highs[-args.box_window:]); box_low = min(lows[-args.box_window:])

    # ---- 箱体识别(硬过滤): 必须"至少两个高点可连成上轨 + 两个低点可连成下轨", 且当前价仍在箱体内 ----
    # 用摆动高/低点聚簇定位上下轨(而非简单取分位数): 单点尖顶/尖底不构成箱体,
    # 已向上突破/向下跌破箱体的标的一律剔除(网格会在破位后持续单边亏损)。
        upper_box, lower, n_hi, n_lo, used_tol, box_days, hi_idx, lo_idx = identify_box(
            highs, lows, args.box_window, args.box_tol,
            min_alternations=args.box_min_alternations,
            lower_rail_stale=args.lower_rail_stale)
        if upper_box is None or lower is None:
            return None, "未形成有效箱体(缺少可连的高低点)"
        # 箱体模式压力/支撑位修正(只扩不缩): 在更长窗口内找"多次触碰"的真实高/低点,
        # 把上界(卖出线)向上扩到最近的压力位、下界(买点)向下扩到最近的支撑位,
        # 使网格边界贴合人眼可见的前期反复触碰位置, 绝不向中间收缩。
        # 与黄金模式一致: 这样区间只变宽、不变窄, 减少"卖飞"(上界太低)与"买早"(下界太高)两类问题。
        _ub_ps, _lb_ps = upper_box, lower
        ps_press, ps_supp = pressure_support_levels(
            highs, lows, args.box_pressure_window,
            bin_frac=args.box_bin_frac, min_touches=args.box_min_touches)
        cand_p = [p for p, _ in ps_press
                  if args.box_pressure_min_gap <= (p / upper_box - 1) * 100.0 <= args.box_pressure_tol]
        if cand_p:
            _ub_ps = min(cand_p)          # 最接近箱体上轨的那个真实压力位(只向上扩)
        cand_s = [s for s, _ in ps_supp
                  if args.box_pressure_min_gap <= (lower / s - 1) * 100.0 <= args.box_pressure_tol]
        if cand_s:
            _lb_ps = max(cand_s)          # 最接近箱体下轨的那个真实支撑位(只向下扩)
        box_ps_used = (_ub_ps != upper_box) or (_lb_ps != lower)
    # 网格上界/中枢(黄金模式=修正后区间线, 直接定; 箱体模式待下方"箱体有效性过滤"后再定最终边界,
    # 以保证突破/触线判定都用箱体真实上下轨, 不被压力/支撑修正值带偏)。
    if is_golden:
        upper = round(upper_box, 4)
        center = (gold_top + gold_bottom) / 2.0
    if not is_golden:
        if box_days < args.box_min_days:
            return None, f"箱体震荡时间不足{args.box_min_days}日"
    # 箱体必须仍在近期有效: 上下轨聚簇成员中最近一个价格回到轨道附近的日子不能太老,
    # 否则说明价格已经离开箱体区域很久, 旧高低点不再代表当前走势。
        last_idx = max((hi_idx + lo_idx) or [0])
        stale_days = args.box_window - 1 - last_idx
        if stale_days > args.box_max_stale_days:
            return None, f"箱体已失效(最近回到轨道附近在{stale_days}日前)"
        if cur > upper_box * 1.002:
            return None, "价格已向上脱离箱体"
    # 真正触线次数: high >= upper*(1-0.1%) 或 low <= lower*(1+0.1%) —— 这是用户看图能数出来的,
    # 与"聚簇成员数"(含近距高位但未真正触线)区分开, 避免报告误导。
        hs_win = highs[-args.box_window:]; ls_win = lows[-args.box_window:]
        touch_hi = sum(1 for i in hi_idx if hs_win[i] >= upper_box * 0.999)
        touch_lo = sum(1 for i in lo_idx if ls_win[i] <= lower * 1.001)
        if cur < lower * 0.998:
            return None, "价格已向下跌破箱体"
    # 箱体模式最终网格边界(放在"箱体有效性过滤"之后, 保证突破/触线判定都用箱体真实上下轨):
    # 上界(卖出线)=真实压力位(若有)或 箱体上轨+upper_buffer% 缓冲; 下界=真实支撑位(若有)或 箱体下轨。
    if not is_golden:
        _sell_base = _ub_ps if box_ps_used else upper_box * (1.0 + args.upper_buffer / 100.0)
        upper = round(_sell_base, 4)
        lower = _lb_ps
        center = (upper + lower) / 2.0
    span = (upper - lower) / lower  # 通道宽度(占下界比例)
    if span <= 0:
        return None, "通道异常"

    # 区间确认说明(用于报告)
    if args.bounds == "golden":
        _pos = (cur - gold_bottom) / (gold_top - gold_bottom) * 100.0 if (gold_top - gold_bottom) > 0 else 0.0
        _ub_note = "(经压力位修正)" if abs(upper - (gold_bottom + (gold_top - gold_bottom) * args.gold_upper)) > 1e-6 else ""
        _lb_note = "(经支撑位修正)" if abs(lower - (gold_bottom + (gold_top - gold_bottom) * args.gold_lower)) > 1e-6 else ""
        confirm_txt = (f"黄金区间: 顶(近{args.gold_window}日最高) <b>{gold_top:.3f}</b> / 零(最低) <b>{gold_bottom:.3f}</b>，"
                       f"现价位于区间 <b>{_pos:.1f}%</b> 位置")
    else:
        _box_ps_note = "（边界已按压力/支撑位修正）" if box_ps_used else ""
        confirm_txt = (f"近{args.box_window}日箱体有效 <b>{box_days}</b> 日 · 上轨碰线 {touch_hi} 次 · "
                       f"下轨碰线 {touch_lo} 次{_box_ps_note}")

    # ---- 箱体横盘确认: 排除下跌趋势 / 持续创新低 ----
    # 近40日线性回归漂移% (正=上行, 负=下行); 以及"近期是否创出40日新低"
    ys = closes[-40:]; n = len(ys)
    mx = (n - 1) / 2.0; my = sum(ys) / n
    sxx = sum((i - mx) ** 2 for i in range(n))
    sxy = sum((i - mx) * (ys[i] - my) for i in range(n))
    slope = sxy / sxx if sxx else 0.0
    drift = slope * (n - 1) / ys[0] * 100.0
    recent_low = min(lows[-10:]); window_low = min(lows[-40:])
    making_new_low = recent_low <= window_low * 1.005   # 近期创出40日新低

    # 黄金模式额外检查: 价格在近 gold_window 日内是否有足够多次上下穿越 MA20,
    # 确保不是单边趋势。穿越次数过少说明无箱体/无震荡, 直接排除。
    ma20_cross = 0
    if is_golden and len(closes) >= 21:
        # 计算收盘价的 20 日简单移动平均
        s = sum(closes[:20])
        ma20s = [s / 20]
        for i in range(20, len(closes)):
            s += closes[i] - closes[i - 20]
            ma20s.append(s / 20)
        # ma20s[j] 对应 closes[j+19]; 在最后 gold_window 日内统计收盘与 MA20 的穿越次数
        n = len(closes)
        start_i = max(20, n - args.gold_window + 1)
        for i in range(start_i, n):
            ma_idx = i - 19  # ma20s 下标
            prev_idx = ma_idx - 1
            if prev_idx < 0 or ma_idx >= len(ma20s):
                continue
            if (closes[i] - ma20s[ma_idx]) * (closes[i - 1] - ma20s[prev_idx]) < 0:
                ma20_cross += 1

    # 当前价在通道内相对位置(0=下界,1=上界), 越居中越安全
    rel = (cur - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

    # 综合打分(0-100, 越高越适合做网格): 黏合好+波动小+振幅稳+价格居中+趋势平
    # 用基准阈值计算, 作为稳定的质量度量(放宽入选时评分偏低, 符合"评分低也保留")
    sc_conv = max(0.0, 1 - conv / args.conv)
    sc_vol = max(0.0, 1 - ann_vol / args.vol)
    sc_amp = max(0.0, 1 - amp20 / args.amp20)
    sc_pos = max(0.0, 1 - 2 * abs(rel - 0.5))
    sc_trend = max(0.0, 1 - abs(drift) / args.trend_max)
    score = 100 * (0.25 * sc_conv + 0.20 * sc_vol + 0.15 * sc_amp
                   + 0.20 * sc_pos + 0.20 * sc_trend)

    # 日均真实波幅(ADR): 该ETF自身历史波动, 用来定"最适合自己"的间距
    # 默认取近1个月(20个交易日); 可用 --adr_window 调整
    aw = min(args.adr_window, len(closes))
    adr = statistics.mean([(highs[i] - lows[i]) / closes[i]
                           for i in range(len(closes) - aw, len(closes))])

    # 最佳间距建议: 日内波幅并非从最低一路走到最高, 真正能用来碰线的约七成,
    # 故取 ADR*0.7, 取整到0.1%; 最低0.6%(v1.0.42: 保底回到0.6%, 它只是参考值不受1%约束)
    best_step_pct = max(round(adr * 100.0 * 0.7, 1), 0.6)
    _cw = min(30, len(closes))
    cross30 = sum(1 for i in range(len(closes) - _cw, len(closes))
                  if (highs[i] - lows[i]) / lows[i] * 100.0 >= best_step_pct)

    if args.grids >= 2:                      # 指定档数 -> 间距由通道均分
        n = args.grids
        step_pct = span / n * 100.0
        step_pct = round(step_pct, 1)
        step_price = (upper - lower) / n
    elif args.step > 0:                      # 指定固定间距%
        step_pct = round(args.step, 1)
        step_price = lower * step_pct / 100.0
        n = max(2, round((upper - lower) / step_price))
    else:                                    # 默认: 网格间距=max(最佳间距,1%), 红字最佳间距独立参考
        # v1.0.42: 主口径(填APP的数) = max(ADR×0.7, 1%) —— 保底1%;
        # 红字"最佳间距"保持独立(保底0.6%), best<主口径时红字行自动显示"比当前更勤"。
        # --adr_mult 设为非1.0 时回到老口径(ADR×倍数, 不足1%取1%)
        if args.adr_mult != 1.0:
            step_pct = adr * 100.0 * args.adr_mult
            if step_pct < 1.0:
                step_pct = 1.0
        else:
            step_pct = max(best_step_pct, 1.0)
        step_pct = round(step_pct, 1)
        step_price = lower * step_pct / 100.0
        n = max(2, round((upper - lower) / step_price))

    channel_pct = span * 100.0               # 通道宽度(%), 用于报告展示

    # 箱体太窄(分不出足够档数)没有网格意义 —— 宁缺毋滥
    if n < args.box_min_grids:
        return None, f"箱体过窄(仅{n}档)"

    # 当前价所处网格档位 (0 = 最下沿)
    level = int((cur - lower) / step_price) if step_price > 0 else 0
    level = max(0, min(n, level))

    # 中枢(=上下界中点) 已在上方区间确定时赋值(箱体模式=上下轨中点; 黄金模式=上下界中点)

    candidate = {
        "code": code, "name": name, "kind": kind,
        "date": dates[-1], "cur": cur, "chg": chg,
        "conv": conv, "amp20": amp20, "amp40": amp40, "ann_vol": ann_vol,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "h40": h40, "l40": l40, "adr": adr * 100.0, "best_step": best_step_pct,
        "cross_days": cross30, "amount_5d": amount_5d, "amount_1d": amount_1d,
        "upper": upper, "lower": lower, "step_pct": step_pct,
        "step_price": step_price, "grids": n, "level": level,
        "channel_pct": channel_pct,
        "drift": drift, "rel": rel, "score": score,
        "center": center, "premium": None, "nav": None, "nav_date": None,
        "box_hits_hi": n_hi, "box_hits_lo": n_lo, "box_tol": used_tol,
        "box_days": box_days,
        "bounds_mode": args.bounds, "gold_top": gold_top, "gold_bottom": gold_bottom,
        "gold_lines": gold_lines, "gold_window": args.gold_window,
        "gold_upper": args.gold_upper, "gold_lower": args.gold_lower,
        "confirm_txt": confirm_txt,
        # 真正"碰线"次数: high >= upper * (1-0.1%) —— 这是用户看图能数出来的触及,
        # 与 box_hits_hi(聚簇成员数, 含近距高位但未触线) 区分开, 避免报告误导。
        "box_touch_hi": touch_hi, "box_touch_lo": touch_lo,
        "dates": dates[-60:], "closes": closes[-60:],
        "ma5s": [ma(closes[:i + 1], 5) for i in range(len(closes) - 60, len(closes))],
        "ma20s": [ma(closes[:i + 1], 20) for i in range(len(closes) - 60, len(closes))],
        "ma60s": [ma(closes[:i + 1], 60) for i in range(len(closes) - 60, len(closes))],
        # 兜底放宽判定用的原始字段
        "_box_high": box_high, "_box_low": box_low, "_making_new_low": making_new_low,
        "_ma20_cross": ma20_cross,
    }
    return candidate, None


# 兜底放宽的逐级阈值倍数:
#   conv/amp20/amp40/vol/trend 放大(越宽松越容易入选);
#   liq 为流动性门槛的"除数", 越大门槛越低(越宽松);
#   box_up/box_dn 为箱体容差, 允许当前价略微超出近40日高低点。
# 第0档=严格默认; 之后逐级放宽, 直到入选数 >= --min_results。
STAGES = [
    {"conv": 1.0, "amp20": 1.0, "amp40": 1.0, "vol": 1.0, "trend": 1.0, "liq": 1.0, "box_up": 1.0,  "box_dn": 1.0},
    {"conv": 1.4, "amp20": 1.4, "amp40": 1.4, "vol": 1.3, "trend": 1.5, "liq": 1.0, "box_up": 1.0,  "box_dn": 1.0},
    {"conv": 2.0, "amp20": 2.0, "amp40": 2.0, "vol": 1.6, "trend": 2.0, "liq": 1.5, "box_up": 1.01, "box_dn": 0.99},
    {"conv": 3.0, "amp20": 3.0, "amp40": 3.0, "vol": 2.0, "trend": 3.0, "liq": 3.0, "box_up": 1.02, "box_dn": 0.98},
]


def passes(c, args, st):
    """按某一档放宽阈值判定标的是否入选; 返回 (bool, 未达标原因)"""
    if c["conv"] > args.conv * st["conv"]:
        return False, "均线黏合不足"
    if c["amp20"] > args.amp20 * st["amp20"]:
        return False, "近1月振幅偏大"
    if c["amp40"] > args.amp40 * st["amp40"]:
        return False, "近2月振幅偏大"
    if c["ann_vol"] > args.vol * st["vol"]:
        return False, "年化波动偏大"
    liq_th = args.min_amount / st["liq"]
    if c["kind"] == "LOF" and c["amount_5d"] < liq_th:
        return False, "LOF流动性不足"
    # A股ETF: 仅 A股 走 1亿 双门槛(用户 v1.0.17: 1亿只针对A股, 不改变原本 T+0 默认池)
    if c["kind"] == "A股ETF":
        if c["amount_5d"] < args.min_amount_a / st["liq"]:
            return False, "A股ETF近5日均成交不足"
        if c["amount_1d"] < args.min_amount_ystd / st["liq"]:
            return False, "A股ETF前一日成交不足"
    # 自动池跨境(QDII): 维持 v1.0.15 的 5000万 近5日均门槛, 前一日不卡
    if c["kind"] == "跨境A" and c["amount_5d"] < MIN_AMOUNT_CROSS / st["liq"]:
        return False, "跨境ETF近5日均成交不足"
    if args.liquid_all and c["kind"] not in ("LOF", "A股ETF", "跨境A") and c["amount_5d"] < liq_th:
        return False, "流动性不足"
    if c["cur"] > c["_box_high"] * st["box_up"]:
        return False, "价格突破箱体上沿"
    if c["cur"] < c["_box_low"] * st["box_dn"]:
        return False, "价格跌破箱体下沿"
    if c["drift"] < -args.trend_max * st["trend"] or (c["_making_new_low"] and c["drift"] < 0):
        return False, "下跌趋势/创新低"
    # 黄金模式额外: 箱体震荡确认。近 gold_window 日收盘价上下穿越 MA20 次数过少,
    # 说明价格单边走(无来回震荡), 即使有高低点也不是"横盘箱体", 直接排除。
    if c["bounds_mode"] == "golden" and c["_ma20_cross"] < args.gold_min_ma20_cross:
        return False, "无箱体震荡(单边趋势)"
    # 溢价硬过滤(安全网): 跨境/LOF ETF 的高溢价是网格实盘隐患——网格按"交易价"设置上下界,
    # 若溢价 13% 时买入, 溢价回落后会立刻亏掉这部分, 等于在错误的高位建网格。
    # 仅当溢价已知(已取到净值)且超过阈值才剔除; 取不到净值(premium=None)则保守保留, 不误杀。
    if c.get("premium") is not None and c["premium"] > args.max_premium:
        return False, f"溢价过高{c['premium']:.1f}%（网格按交易价设, 溢价回落后额外亏损）"
    return True, ""


def relax_select(candidates, args, min_n):
    """逐级放宽阈值直到入选 >= min_n 只; min_n<=0 时只取严格达标(第0档)。
       候选按评分降序填充, 一旦达到 min_n 即停止, 因此结果"至少 min_n 只"且偏向高分。
       返回 (入选候选列表, 实际用到的最高放宽档位)。"""
    if min_n <= 0:
        return [c for c in candidates if passes(c, args, STAGES[0])[0]], 0
    if not candidates:
        return [], 0
    ordered = sorted(candidates, key=lambda c: c["score"], reverse=True)
    selected, seen = [], set()
    stage = 0
    for i, st in enumerate(STAGES):
        for c in ordered:
            if c["code"] in seen:
                continue
            # 第0档(严格)全收; 放宽档位一旦达到 min_n 即停止, 保留高分标的
            if i > 0 and len(selected) >= min_n:
                break
            ok, _ = passes(c, args, st)
            if ok:
                selected.append(c); seen.add(c["code"])
        stage = i
        if len(selected) >= min_n:
            break
    return selected, stage


def load_universe(path):
    if not path:
        return [(c, n, k) for c, n, k in UNIVERSE]
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out.append((row["code"].strip(), row.get("name", "").strip(), row.get("kind", "").strip()))
    return out


# ---- 股票型 ETF 池(A股 + 跨境QDII): 自动从东方财富拉全市场 ETF, 剔除货币/债券/商品后并入 ----
A_SHARE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "a_share_etf_pool.json")
MIN_AMOUNT_CROSS = 50000000.0   # 自动池跨境(QDII)近5日均成交额门槛(5000万, v1.0.15 标准); 前一日不卡

# v1.0.32: 池快照新鲜度元信息。交付包内置了一份全市场 ETF 名单快照(拉取名单的接口
# push2.eastmoney.com 在部分网络下会被掐断, 导致无法自刷新), 因此快照会随时间变旧。
# 这里记录快照生成日期/天数/是否过期/刷新是否失败, 供控制台与报告显式提示, 绝不静默使用旧名单。
A_POOL_META = {"date": None, "age_days": None, "stale": False, "refresh_failed": False}

def _classify_aetf(name, code):
    """把一只 ETF 归类为 '货币'/'债券'/'商品'/'跨境'/'股票A'; '股票A' 与 '跨境' 均留作网格池(A股 + 跨境股票型ETF)。"""
    n = name
    # 上交所跨境 ETF 专用代码段 513xxx -> 跨境(QDII)
    if code.startswith("513"):
        return "跨境"
    if "货币" in n:
        return "货币"
    if any(k in n for k in ["国债", "转债", "信用债", "地方债", "城投债", "公司债",
                             "短融", "政金债", "国开债", "农发债", "铁道债", "证金债",
                             "十年国债", "30年国债", "债券", "可转债"]):
        return "债券"
    # 商品(注意"黄金股"是股票型, 含'股'字时不当商品)
    if "黄金" in n and "股" in n:
        pass
    elif any(k in n for k in ["黄金", "豆粕", "有色", "商品", "原油", "白银", "铜",
                               "铁矿石", "能化", "化工", "农产品", "能源"]):
        return "商品"
    if any(k in n for k in ["港股", "恒生", "香港", "美股", "纳指", "纳斯达克", "标普",
                             "道琼斯", "日经", "东证", "德国", "法国", "沙特", "东南亚",
                             "印度", "中概", "海外", "全球", "亚太", "英国", "韩国", "越南",
                             "泰国", "巴西", "富时", "罗素", "MSCI", "美国", "日本",
                             "CAC", "DAX", "标普500", "纳指100"]):
        return "跨境"
    return "股票A"


# ---- 跟踪指数/主题识别(用于"同指数去重"): 由 ETF 名称推断其跟踪的指数或主题 ----
# 同一指数往往有多只 ETF(如华安/易方达上证50ETF), 名称不同但走势高度同质, 做网格只需留评分最高一只。
# 规则: 取名称中"匹配最长关键词"对应的规范指数/主题名; 未匹配到则返回 None(视为独立标的, 绝不误并)。
INDEX_KEYWORDS = [
    # ===== 宽基 =====
    ("MSCI中国A50", "MSCI中国A50"),
    ("中证A500", "中证A500"), ("A500", "中证A500"),   # 注意: A500 必须排在 A50 之前被"最长匹配"选中, 否则 A50 会误吞 A500
    ("A50", "MSCI中国A50"),
    ("上证380", "上证380"), ("上证180", "上证180"), ("上证50", "上证50"),
    ("沪深300", "沪深300"),
    ("中证1000", "中证1000"), ("中证800", "中证800"), ("中证500", "中证500"),
    ("科创100", "科创100"), ("科创板50", "科创50"), ("科创50", "科创50"),
    ("创业板50", "创业板50"), ("创业板", "创业板"),
    ("深证100", "深证100"), ("深证成指", "深证成指"), ("北证50", "北证50"),
    ("科创创业", "双创"), ("双创", "双创"),
    # ===== 跨境宽基 =====
    ("纳斯达克100", "纳斯达克"), ("纳指100", "纳斯达克"), ("纳斯达克", "纳斯达克"), ("纳指", "纳斯达克"),
    ("标普500", "标普500"), ("标普", "标普500"),
    ("恒生科技", "恒生科技"), ("恒生医疗", "恒生医疗"), ("恒生", "恒生"),
    ("港股通", "港股"), ("港股", "港股"),
    ("中国互联网", "中概互联"), ("中概", "中概互联"),
    ("日经", "日经"), ("东证", "东证"), ("德国", "德国DAX"), ("法国", "法国CAC"),
    ("英国", "英国富时"), ("印度", "印度"), ("越南", "越南"), ("沙特", "沙特"),
    ("道琼斯", "道琼斯"),
    # ===== 行业/主题 =====
    ("券商", "券商"), ("证券", "券商"),
    ("银行", "银行"), ("保险", "保险"),
    ("军工", "军工"),
    ("创新药", "医药"), ("生物医药", "医药"), ("医疗", "医药"), ("医药", "医药"),
    ("白酒", "消费"), ("食品饮料", "消费"), ("家电", "消费"), ("酒", "消费"), ("消费", "消费"),
    ("科创芯片", "半导体"), ("芯片", "半导体"), ("半导体", "半导体"),
    ("新能源车", "新能源"), ("锂电", "新能源"), ("电池", "新能源"), ("光伏", "新能源"), ("新能源", "新能源"),
    ("黄金股", "黄金股"), ("黄金", "黄金"),
    ("红利", "红利"), ("高股息", "红利"),
    ("游戏", "传媒"), ("传媒", "传媒"),
    ("5G", "通信"), ("通信", "通信"),
    ("人工智能", "AI"), ("AI", "AI"), ("软件", "计算机"), ("计算机", "计算机"),
    ("云计算", "云计算"), ("大数据", "大数据"),
    ("机器人", "机器人"),
    ("稀土", "有色"), ("有色金属", "有色"), ("有色", "有色"),
    ("煤炭", "煤炭"), ("钢铁", "钢铁"), ("电力", "电力"),
    ("化工", "化工"), ("石化", "化工"),
    ("房地产", "地产"), ("地产", "地产"),
    ("基建", "基建"), ("建筑", "基建"),
    ("畜牧", "养殖"), ("养殖", "养殖"), ("农业", "农业"),
    ("旅游", "旅游"), ("环保", "环保"), ("碳中和", "碳中和"),
    ("物流", "物流"), ("汽车", "汽车"),
    ("自由现金流", "自由现金流"), ("现金流", "自由现金流"),
    ("上证综指", "上证综指"), ("MSCIA股", "MSCI A股"), ("工程机械", "工程机械"),
    ("一带一路", "一带一路"), ("央企", "央企"), ("国企", "央企"),
]


def track_index_key(name):
    """返回 ETF 名称对应的规范指数/主题名, 无匹配返回 None。"""
    best_key, best_len = None, 0
    for kw, key in INDEX_KEYWORDS:
        if kw in name and len(kw) > best_len:
            best_key, best_len = key, len(kw)
    return best_key


def dedup_by_index(candidates, args=None):
    """同跟踪指数/主题只保留综合评分最高一只; 未识别到指数的独立标的全部保留。
       v1.0.31: 组内优先保留"流动性达标"的标的——此前只按评分选代表, 若评分最高者
       成交额不足门槛, 后续流动性硬过滤会把整个指数/主题全灭, 而同组内真正主流
       (成交活跃、用户实际会买)的标的却已被当"次优"合并掉(如 上证50 被 建信/天弘
       代表, 二者近5日均不足1亿被砍, 主流的 510050 反而消失)。
       返回 (去重后列表, 被合并去掉的只数, 合并明细[(保留名, 去掉名列表)])。"""
    def _liq_ok(c):
        """该标的是否满足自身类别的流动性硬门槛(严格口径, 不计放宽档)"""
        if args is None:
            return True
        if c["kind"] == "A股ETF":
            return (c.get("amount_5d", 0) >= args.min_amount_a
                    and c.get("amount_1d", 0) >= args.min_amount_ystd)
        if c["kind"] == "LOF":
            return c.get("amount_5d", 0) >= args.min_amount
        if c["kind"] == "跨境A":
            return c.get("amount_5d", 0) >= MIN_AMOUNT_CROSS
        if args.liquid_all:
            return c.get("amount_5d", 0) >= args.min_amount
        return True   # T+0 跨境/黄金/商品等默认池标的不卡流动性

    groups = {}
    for c in candidates:
        k = track_index_key(c["name"])
        groups.setdefault(k, []).append(c)
    kept, dropped, details = [], 0, []
    for k, lst in groups.items():
        if k is None or len(lst) == 1:
            for c in lst:
                c["index_key"] = k
                kept.append(c)
        else:
            # 先按"流动性达标"再按评分降序: 达标者优先当代表, 避免整组被流动性过滤全灭
            lst_sorted = sorted(lst, key=lambda x: (_liq_ok(x), x["score"]), reverse=True)
            best = lst_sorted[0]
            best["index_key"] = k
            kept.append(best)
            drop_names = [c["name"] for c in lst_sorted[1:]]
            dropped += len(drop_names)
            details.append((best["name"], drop_names))
    kept.sort(key=lambda c: c["score"], reverse=True)
    return kept, dropped, details


def _read_pool_cache():
    """读取本地池快照; 返回 (列表, 快照mtime) ; 无/损坏返回 (None, None)。兼容旧2元素格式。"""
    if not os.path.exists(A_SHARE_CACHE):
        return None, None
    try:
        with open(A_SHARE_CACHE, encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return None, None
        out = []
        for c in data:
            if len(c) >= 3:
                code, name, k = c[0], c[1], c[2]
            else:
                code, name = c[0], c[1]
                k = "A股ETF" if _classify_aetf(name, code) == "股票A" else "跨境A"
            out.append((code, name, k))
        return out, os.path.getmtime(A_SHARE_CACHE)
    except Exception:
        return None, None


def _fetch_pool_em_board():
    """主源: 东方财富行情中心的 ETF 板块(b:MK0021)分页拉取。失败返回空列表。"""
    seen = {}
    total = None
    pn = 1
    fail = 0
    while True:
        # 首页用较少重试快速探活: 主源被掐断时不必苦等全程重试, 尽快交给备用源
        diff, tot = _pull_em_page(pn, retries=(2 if pn == 1 else 5))
        if diff is None:
            if pn == 1:
                return []   # 首页即失败 -> 判定主源不可用, 立即切换备用源
            fail += 1
            if fail >= 5:
                break
            continue
        fail = 0
        if total is None:
            total = tot
        for it in diff:
            code = it.get("f12")
            name = it.get("f14")
            if code and name:
                seen[code] = name
        if total is not None and len(seen) >= total:
            break
        if not diff:
            break
        if pn > 200:
            break
        pn += 1
        time.sleep(0.8)
    out = [(code, name, "A股ETF" if _classify_aetf(name, code) == "股票A" else "跨境A")
           for code, name in seen.items()
           if _classify_aetf(name, code) in ("股票A", "跨境")]
    return out


# ---- v1.0.33 备用名单源 ----------------------------------------------------
# 主源 push2.eastmoney.com 在部分网络环境下会被掐断连接(RemoteDisconnected), 导致名单
# 永远刷不动。备用源走 fund.eastmoney.com(与天天基金净值接口同域, 实测可达)的全量基金
# 代码文件, 按"类型=指数型-股票" + "场内 ETF 代码前缀" + 沿用脚本自带分类器还原名单。
FUNDCODE_SEARCH_URL = "https://fund.eastmoney.com/js/fundcode_search.js"
# 场内 ETF 代码前缀(3位)。由现有名单快照反推验证: 可还原 99.3% 的快照条目, 且能纳入
# 此后新上市的同类 ETF; 同时天然排除 场外基金(000/001/.../519)、LOF(16x/501/502)、
# QDII(513/520) 等非本池标的。511/518 虽为债券/黄金 ETF, 会被分类器剔除, 保留无副作用。
ETF_CODE_PREFIXES = ("159", "510", "511", "512", "515", "516", "517", "518",
                     "530", "560", "561", "562", "563", "588", "589")


def _fetch_pool_from_fundcode():
    """备用源: 天天基金全量基金代码文件。成功返回 [(code,name,kind),...], 失败返回 []。"""
    try:
        req = urllib.request.Request(FUNDCODE_SEARCH_URL, headers={
            "User-Agent": UA, "Referer": "https://fund.eastmoney.com/"})
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        m = re.search(r"var\s+r\s*=\s*(\[.*?\]);", raw, re.S)
        if not m:
            return []
        out, seen = [], set()
        for item in json.loads(m.group(1)):
            if len(item) < 4:
                continue
            code, name, ftype = str(item[0]), str(item[2]), str(item[3])
            if ftype != "指数型-股票":
                continue
            if not code.startswith(ETF_CODE_PREFIXES) or code in seen:
                continue
            k = _classify_aetf(name, code)
            if k not in ("股票A", "跨境"):
                continue
            seen.add(code)
            out.append((code, name, "A股ETF" if k == "股票A" else "跨境A"))
        return out
    except Exception:
        return []


def _fetch_pool_online():
    """联网拉全市场 ETF: 先试主源(行情中心板块), 失败再试备用源(天天基金代码文件)。
       任一成功则写入本地快照并返回; 都失败返回空列表。"""
    for fn in (_fetch_pool_em_board, _fetch_pool_from_fundcode):
        out = fn()
        if out:
            try:
                with open(A_SHARE_CACHE, "w", encoding="utf-8") as f:
                    json.dump([[c, n, k] for c, n, k in out], f, ensure_ascii=False)
            except Exception:
                pass
            return out
    return []


def fetch_a_share_etf_codes(refresh=False, max_age_days=30):
    """取全市场 ETF 池: 优先读本地快照, 快照超过 max_age_days 天则先尝试联网刷新。
       结果缓存到脚本同目录 a_share_etf_pool.json; --refresh_a_pool 可强制联网。
       v1.0.32: 把快照新鲜度写入 A_POOL_META(生成日期/天数/是否过期/刷新是否失败)。
       联网失败时退回旧快照(哪怕已过期), 完全没有快照才返回空列表(退化为内置 T+0 池)。"""
    global A_POOL_META
    A_POOL_META = {"date": None, "age_days": None, "stale": False, "refresh_failed": False}

    def _stamp(mtime):
        if mtime:
            A_POOL_META["date"] = time.strftime("%Y-%m-%d", time.localtime(mtime))
            A_POOL_META["age_days"] = int((time.time() - mtime) / 86400.0)

    if not refresh:
        cached, mtime = _read_pool_cache()
        if cached:
            _stamp(mtime)
            if mtime and (time.time() - mtime) / 86400.0 > max_age_days:
                A_POOL_META["stale"] = True          # 快照过期: 先试联网刷新再用
                fresh = _fetch_pool_online()
                if fresh:
                    _stamp(time.time())
                    A_POOL_META["stale"] = False
                    return fresh
                A_POOL_META["refresh_failed"] = True  # 刷新失败: 沿用旧名单但显式标记
            return cached

    fresh = _fetch_pool_online()
    if fresh:
        _stamp(time.time())
        return fresh
    A_POOL_META["refresh_failed"] = True
    cached, mtime = _read_pool_cache()   # 联网失败: 退回旧快照也远好过只剩 96 只内置池
    if cached:
        _stamp(mtime)
        A_POOL_META["stale"] = True
        return cached
    return []


def _pull_em_page(pn, pz=100, retries=5):
    """拉东方财富 ETF 列表单页(每页100, 匿名请求上限), 带重试。返回 (diff列表, total) 或 (None, None)。"""
    for t in range(retries):
        try:
            qs = urllib.parse.urlencode({"pn": str(pn), "pz": str(pz), "po": "1",
                                         "np": "1", "fltt": "2", "invt": "2", "fid": "f3",
                                         "fs": "b:MK0021", "fields": "f12,f14"})
            url = "https://push2.eastmoney.com/api/qt/clist/get?" + qs
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Referer": "https://quote.eastmoney.com/"})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read())
            return (d.get("data") or {}).get("diff") or [], (d.get("data") or {}).get("total")
        except Exception:
            if t < retries - 1:
                time.sleep(1.5 * (t + 1))
    return None, None


def fmt(x, d=3):
    return f"{x:.{d}f}"


def sparkline_html(r, w=640, h=220):
    """纯 Python 生成 SVG: 价格 + 三条均线 + 上下界网格线 (美化版)"""
    closes = r["closes"]; dates = r["dates"]
    xs = list(range(len(closes)))
    allv = list(closes) + [r["upper"], r["lower"]]
    for s in (r["ma5s"], r["ma20s"], r["ma60s"]):
        allv += [v for v in s if v is not None]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    pad_l, pad_r, pad_t, pad_b = 10, 10, 16, 22
    def X(i):
        return pad_l + (w - pad_l - pad_r) * i / (len(xs) - 1)
    def Y(v):
        return pad_t + (h - pad_t - pad_b) * (hi - v) / (hi - lo)

    svg = [f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="xMidYMid meet" '
           f'style="border-radius:10px">']
    # 背景渐变
    svg.append(f'<defs>'
               f'<linearGradient id="bg{r["code"]}" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="#fafbff"/><stop offset="100%" stop-color="#f0f1f7"/>'
               f'</linearGradient>'
               f'<linearGradient id="area{r["code"]}" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="#6366f1" stop-opacity="0.18"/>'
               f'<stop offset="100%" stop-color="#6366f1" stop-opacity="0.01"/>'
               f'</linearGradient>'
               f'<linearGradient id="ch{r["code"]}" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="#fee2e2" stop-opacity="0.5"/>'
               f'<stop offset="100%" stop-color="#dcfce7" stop-opacity="0.5"/>'
               f'</linearGradient>'
               f'</defs>')
    svg.append(f'<rect width="{w}" height="{h}" fill="url(#bg{r["code"]})" rx="10" ry="10"/>')
    # 通道区域填充
    svg.append(f'<rect x="{pad_l}" y="{Y(r["upper"]):.1f}" width="{w-pad_l-pad_r}" '
               f'height="{Y(r["lower"])-Y(r["upper"]):.1f}" fill="url(#ch{r["code"]})" rx="2"/>')
    # 水平网格线
    for frac in (0.25, 0.5, 0.75):
        gy = pad_t + (h - pad_t - pad_b) * frac
        svg.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{w-pad_r}" y2="{gy:.1f}" '
                   f'stroke="#e5e7eb" stroke-width="0.5" stroke-dasharray="2 3"/>')
    # 上下界
    svg.append(f'<line x1="{pad_l}" y1="{Y(r["upper"]):.1f}" x2="{w-pad_r}" y2="{Y(r["upper"]):.1f}" '
               f'stroke="#ef4444" stroke-width="1.2" stroke-dasharray="6 4"/>')
    svg.append(f'<line x1="{pad_l}" y1="{Y(r["lower"]):.1f}" x2="{w-pad_r}" y2="{Y(r["lower"]):.1f}" '
               f'stroke="#22c55e" stroke-width="1.2" stroke-dasharray="6 4"/>')
    svg.append(f'<text x="{w-pad_r}" y="{Y(r["upper"])-4:.1f}" fill="#ef4444" font-size="10" font-weight="600" text-anchor="end">上界 {fmt(r["upper"])}</text>')
    svg.append(f'<text x="{w-pad_r}" y="{Y(r["lower"])+13:.1f}" fill="#22c55e" font-size="10" font-weight="600" text-anchor="end">下界 {fmt(r["lower"])}</text>')

    # 黄金分割参考线(仅黄金模式): 画出 0.236/0.382/中(0.5)/0.618/0.809 五条内部黄金线
    if r.get("gold_lines") and len(r["gold_lines"]) >= 7:
        for _gi in (1, 2, 3, 4, 5):
            _gv = r["gold_lines"][_gi]
            if _gv <= r["lower"] or _gv >= r["upper"]:
                continue
            _bold = 1.1 if _gi == 3 else 0.7
            svg.append(f'<line x1="{pad_l}" y1="{Y(_gv):.1f}" x2="{w-pad_r}" y2="{Y(_gv):.1f}" '
                       f'stroke="#f59e0b" stroke-width="{_bold}" stroke-dasharray="2 4" opacity="0.65"/>')

    def poly(vals, color, width, dash=""):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="{width}"{da} points="{pts}"/>')

    poly(r["ma60s"], "#f59e0b", 1.0, "3 2")
    poly(r["ma20s"], "#3b82f6", 1.0, "3 2")
    poly(r["ma5s"], "#a855f7", 1.0, "3 2")
    # 价格面积填充
    close_pts = [(X(i), Y(v)) for i, v in enumerate(closes) if v is not None]
    if close_pts:
        area_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in close_pts)
        area_pts += f" {close_pts[-1][0]:.1f},{h-pad_b:.1f} {close_pts[0][0]:.1f},{h-pad_b:.1f}"
        svg.append(f'<polygon fill="url(#area{r["code"]})" points="{area_pts}"/>')
    poly(closes, "#1e293b", 1.8)
    # 当前价点
    svg.append(f'<circle cx="{X(len(closes)-1):.1f}" cy="{Y(closes[-1]):.1f}" r="4" fill="#1e293b" stroke="#fff" stroke-width="1.5"/>')
    svg.append(f'<circle cx="{X(len(closes)-1):.1f}" cy="{Y(closes[-1]):.1f}" r="7" fill="none" stroke="#1e293b" stroke-width="1" opacity="0.3"/>')
    svg.append(f'<text x="{pad_l}" y="12" fill="#94a3b8" font-size="9" font-weight="500">{dates[0]}  →  {dates[-1]}</text>')
    svg.append('</svg>')
    return "".join(svg)


def render_html(results, args, out_path=None, fillnote="", extra_html="", dedup_line=""):
    """渲染筛选报告 HTML。
       out_path: 若提供则同时写入文件; 若为 None 则只返回字符串(供网页版用)。
       extra_html: 插入到 hero 与 method 之间, 用于网页版嵌入参数表单。"""
    # v1.0.32: 把全市场名单快照日期写进页脚, 让报告读者也能看到名单新鲜度
    _pm = A_POOL_META
    if _pm.get("date"):
        if _pm.get("stale") and _pm.get("refresh_failed"):
            _tag = "已超过建议天数且联网刷新失败，可能缺少此后新上市的 ETF"
        elif _pm.get("stale"):
            _tag = "已超过建议天数"
        else:
            _tag = "较新"
        pool_note = f"全市场 ETF 名单快照：{_pm['date']}（{_pm['age_days']} 天前，{_tag}）。<br>"
    elif results:
        pool_note = ""
    else:
        pool_note = ""
    rows = []
    for idx, r in enumerate(results, 1):
        up = r["chg"] >= 0
        color = "#ef4444" if up else "#22c55e"
        sign = "+" if up else ""
        amt = r["amount_5d"]
        amt_str = f"{amt/1e8:.2f}亿" if amt >= 1e8 else f"{amt/1e4:.1f}万"
        amt1 = r["amount_1d"]
        amt1_str = f"{amt1/1e8:.2f}亿" if amt1 >= 1e8 else f"{amt1/1e4:.1f}万"
        rec = ' <span class="rec">★ 推荐</span>' if idx <= 3 else ""
        # 溢价率展示
        if r["premium"] is not None:
            pm = r["premium"]
            pm_color = "#ef4444" if pm > 3 else ("#22c55e" if pm < -3 else "#475569")
            pm_str = f"{pm:+.2f}%"
            pm_badge = f' <span class="pm-warn">溢价{pm:.1f}%⚠</span>' if pm > 3 else (f' <span class="pm-ok">折价{pm:.1f}%</span>' if pm < -3 else "")
            # 高溢价风险提示: 网格按交易价设置, 溢价回落后会额外亏损(尤其跨境/LOF)
            risk_note = (f"⚠ 当前溢价 <b>{pm:.1f}%</b>：网格按交易价设上下界，溢价回落后会额外亏损，请谨慎。"
                         if pm > 3 else "")
        else:
            pm_str = "—"; pm_color = "#94a3b8"; pm_badge = ""; risk_note = ""
        # 现价相对中枢位置
        pos = (r["cur"] / r["center"] - 1) * 100.0
        pos_txt = f"现价高于中枢 {pos:.1f}%" if pos > 0 else f"现价低于中枢 {-pos:.1f}%"
        # 最佳间距文案: 主口径(网格间距)保底1%; 红字最佳间距独立(保底0.6%), best<主口径时显示"更勤"对比;
        # 默认口径下波幅小的票就会出现 best(0.6保底) < 主口径(1保底); --step/--grids 指定时同样可能
        if r["best_step"] < r["step_pct"] - 1e-9:
            best_txt = (f"<span style=\"color:#dc2626;font-weight:800;font-size:1.15em\">{fmt(r['best_step'],1)}%</span>"
                        f"（按日均波幅约七成定，近30日约 {r['cross_days']} 天穿线，比当前 {fmt(r['step_pct'],1)}% 更勤）。"
                        f"是否照抄看你的费率：每格利润要盖得住手续费，费率高请保留当前间距")
        else:
            _adr_def = max(round(r["adr"], 1), 1.0)
            best_txt = (f"<span style=\"color:#dc2626;font-weight:800;font-size:1.15em\">{fmt(r['step_pct'],1)}%</span>"
                        f"（按日均波幅约七成定，近30日约 {r['cross_days']} 天穿线，直接抄进券商APP）。"
                        f"费率偏高可放宽到约 {_adr_def:.1f}%（日均波幅原值）")
        # 大白话"为什么适合网格": 用真实指标现场拼一句, 让非技术学员一看就懂(回应"凭什么选它")
        _why = []
        if r["conv"] <= 3.0:
            _why.append(f"均线黏合{r['conv']:.1f}%")
        if abs(r["drift"]) <= 3.0:
            _why.append("趋势平稳")
        elif abs(r["drift"]) <= args.trend_max:
            _why.append("趋势未走极端")
        if 0.35 <= r["rel"] <= 0.65:
            _why.append("价格居中")
        if r["amp20"] <= 6.0:
            _why.append("振幅温和")
        why = ("适合做网格：" + "、".join(_why) + "。") if _why else "综合评分达标。"
        # 评分等级颜色(榜内折算分: 60~95)
        sc = r["score_disp"]
        sc_grad = "linear-gradient(135deg,#6366f1,#8b5cf6)" if sc >= 85 else ("linear-gradient(135deg,#3b82f6,#06b6d4)" if sc >= 72 else "linear-gradient(135deg,#64748b,#94a3b8)")
        # v1.0.35: 下界口径标注——不同工具/小程序取法不同, 明示口径避免学员跨工具对比时困惑
        if args.bounds == "golden":
            bound_desp = f"黄金分割口径（近{args.gold_window}日顶底按比例分割，非最低价）"
        else:
            bound_desp = "箱体支撑线口径：反复触碰的低点连线（非历史最低价）——与其他工具按最低价算的结果不同属正常"

        rows.append(f"""
        <div class="card{' card-rec' if idx <= 3 else ''}">
          <div class="hd">
            <span class="rank">#{idx}</span>
            <span class="nm">{r['name']}</span>
            <span class="cd">{r['code']}</span>
            <span class="kd kd-{r['kind'].replace('跨境A','跨境')}">{r['kind'].replace('跨境A','跨境')}</span>
            {f'<span class="idx">{r["index_key"]}</span>' if r.get("index_key") else ""}
            <span class="score" style="background:{sc_grad}">评分 {r['score_disp']:.1f}</span>{rec}
            <span class="pr" style="color:{color}">{fmt(r['cur'])} <em>{sign}{fmt(r['chg'],1)}%</em></span>
          </div>
          {sparkline_html(r)}
          <div class="keybox">
            <div class="kcell"><span class="kl">上界(卖出线)</span><b class="kv">{fmt(r['upper'])}</b></div>
            <div class="kcell"><span class="kl">下界</span><b class="kv">{fmt(r['lower'])}</b></div>
            <div class="kcell"><span class="kl">中枢 / 基准价</span><b class="kv">{fmt(r['center'])}</b></div>
            <div class="kcell"><span class="kl">网格间距</span><b class="kv">{fmt(r['step_pct'],1)}%</b><span class="kv2">{fmt(r['step_price'])}元</span></div>
          </div>
          <div class="hint"><b>基准价填「中枢」，间距填 {fmt(r['step_pct'],1)}%</b>（=日均波幅约七成，保底1%，直接抄进券商APP）。通道宽 {fmt(r['channel_pct'],1)}%，共 {r['grids']} 格。{pos_txt}</div>
          <div class="why">{why}</div>
          {f'<div class="warn">{risk_note}</div>' if risk_note else ""}
          <table class="kv">
            <tr><td>均线黏合度</td><td>{fmt(r['conv'],1)}%</td><td>近1月振幅</td><td>{fmt(r['amp20'],1)}%</td></tr>
            <tr><td>近2月振幅</td><td>{fmt(r['amp40'],1)}%</td><td>年化波动率</td><td>{fmt(r['ann_vol'],1)}%</td></tr>
            <tr><td>趋势漂移(40日)</td><td>{fmt(r['drift'],1)}%</td><td>日均波幅ADR</td><td>{fmt(r['adr'],1)}%（近{args.adr_window}日）</td></tr>
            <tr><td>溢价率</td><td style="color:{pm_color};font-weight:700">{pm_str}{pm_badge}</td><td>净值日期</td><td>{r['nav_date'] or '—'}</td></tr>
            <tr><td>当前所处档</td><td>第 {r['level']} 档 / 共 {r['grids']} 格</td><td>近5日均成交额</td><td>{amt_str}（估算）</td></tr>
            <tr><td>前一日成交额</td><td colspan="3">{amt1_str}（估算）</td></tr>
            <tr><td>最佳间距</td><td colspan="3">{best_txt}</td></tr>
            <tr><td>区间确认</td><td colspan="3">{r['confirm_txt']}</td></tr>
            <tr><td>下界口径</td><td colspan="3">{bound_desp}</td></tr>
          </table>
        </div>""")
    if args.bounds == "golden":
        method = (f"①均线黏合（MA5/10/20/60离散度≤{args.conv}%）；②横盘震荡（近1月振幅≤{args.amp20}%、"
                  f"近2月振幅≤{args.amp40}%、年化波动≤{args.vol}%）；"
                  f"③<b>黄金分割区间（硬条件）：取近{args.gold_window}日最高价作「顶」、最低价作「零」</b>"
                  f"（仿通达信主力黄金线公式，不含最近{args.gold_lag}日以避免极值干扰），"
                  f"默认上界取「六一八」线、下界取「三八二」线（可用 --gold_upper/--gold_lower 改成八零九/二三六等）；"
                  f"④<b>压力/支撑位修正</b>：回看近{args.gold_pressure_window}日，找出价格反复触碰（≥{args.gold_min_touches}次）的真实压力位/支撑位——"
                  f"现价贴近上界时把上界上修到最近的压力位（多次触碰的高点），存在明显更深的支撑位时把下界下修到该支撑位，"
                  f"这样区间只扩宽、不缩窄，也更贴合人眼可见的前期反复触碰位置；"
                  f"当前价必须落在最终区间之内——已突破上沿或跌破下沿的一律不选；"
                  f"⑤短期趋势：近40日漂移跌破-{args.trend_max}% 或近期创40日新低也剔除。"
                  f"网格上界=修正后的区间最高线, 下界=修正后的区间最低线, 中枢=上下界中点; "
                  f"网格间距取该ETF日均波幅的约七成（保底1%，每只不同）——费率偏高者可自行放宽间距。"
                  f"⑥高溢价硬过滤：跨境/LOF ETF 溢价率超过 --max_premium%（默认10%）直接剔除——网格按交易价设上下界，溢价回落后会额外亏损（已入选标的报告内仍标注溢价率）。" f"按「综合评分」降序排列（满分100，按榜内相对水平折算，榜首≈95分），前3只标★推荐。")
    else:
        method = (f"①均线黏合（MA5/10/20/60离散度≤{args.conv}%）；②横盘震荡（近1月振幅≤{args.amp20}%、"
                  f"近2月振幅≤{args.amp40}%、年化波动≤{args.vol}%）；"
                  f"③<b>箱体有效性（硬条件）：近{args.box_window}日内必须至少有两个高点价格接近、"
                  f"能连成一条上轨，两个低点价格接近、能连成一条下轨</b>"
                  f"（判定宽度 {args.box_tol}%，即高低点之间相差不超过这个幅度才算同一水平线），"
                  f"且当前价必须仍在箱体之内——已向上突破或向下跌破的一律不选；"
                  f"④短期趋势：近40日漂移跌破-{args.trend_max}% 或近期创40日新低也剔除。"
                  f"⑤<b>压力/支撑位修正</b>：回看近{args.box_pressure_window}日，找出价格反复触碰（≥{args.box_min_touches}次）的真实压力位/支撑位——"
                  f"把网格上界(卖出线)向上扩到最近的压力位（多次触碰的高点），把下界(买点)向下扩到最近的支撑位，"
                  f"这样区间只扩宽、不缩窄，更贴合人眼可见的前期反复触碰位置、减少卖飞与买早；"
                  f"若找不到这样的压力/支撑位，则上界沿用箱体上轨加{args.upper_buffer:.1f}%缓冲、下界取箱体下轨触及价（不再用分位数估算）。"
                  f"网格间距取该ETF日均波幅的约七成（保底1%，每只不同）——费率偏高者可自行放宽间距。"
                  f"⑥高溢价硬过滤：跨境/LOF ETF 溢价率超过 --max_premium%（默认10%）直接剔除——网格按交易价设上下界，溢价回落后会额外亏损（已入选标的报告内仍标注溢价率）。" f"按「综合评分」降序排列（满分100，按榜内相对水平折算，榜首≈95分），前3只标★推荐。")
    # 不显示"数量兜底"说明（min_results 默认仍生效，保证结果不低于 --min_results 只）
    # 统计
    cats = {}
    for r in results:
        cats[r["kind"].replace("跨境A", "跨境")] = cats.get(r["kind"].replace("跨境A", "跨境"), 0) + 1
    cat_str = " · ".join(f"{k}{v}" for k, v in sorted(cats.items(), key=lambda x: -x[1]))
    top_score = results[0]["score_disp"] if results else 0
    avg_score = sum(r["score_disp"] for r in results) / len(results) if results else 0
    prem_high = sum(1 for r in results if r["premium"] and r["premium"] > 3)
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>网格交易筛选报告</title>
<style>
 *{{box-sizing:border-box}}
 body{{font-family:-apple-system,"Microsoft YaHei","Segoe UI",sans-serif;background:linear-gradient(180deg,#667eea 0%,#764ba2 8%,#f1f2f8 14%);margin:0;color:#1e293b;min-height:100vh}}
 .wrap{{max-width:960px;margin:0 auto;padding:16px 16px 40px}}
 .hero{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:20px;padding:28px 24px 20px;color:#fff;margin-bottom:16px;box-shadow:0 8px 32px rgba(102,126,234,.3);position:relative;overflow:hidden}}
 .hero::after{{content:"";position:absolute;top:-30px;right:-30px;width:180px;height:180px;background:rgba(255,255,255,.08);border-radius:50%}}
 .hero h1{{font-size:26px;margin:0 0 6px;font-weight:800;letter-spacing:1px;position:relative;z-index:1}}
 .hero .sub{{font-size:13px;opacity:.85;margin-bottom:14px;position:relative;z-index:1}}
 .dedup-note{{margin:14px 0 4px;padding:11px 16px;background:#ecfdf5;border-left:4px solid #10b981;border-radius:10px;font-size:13px;color:#065f46}} .dedup-note b{{color:#047857}}
 .why{{margin:8px 0 2px;padding:8px 12px;background:#f0f9ff;border-left:4px solid #0ea5e9;border-radius:10px;font-size:12.5px;color:#0c4a6e}}
 .warn{{margin:8px 0 2px;padding:8px 12px;background:#fef2f2;border-left:4px solid #ef4444;border-radius:10px;font-size:12.5px;color:#b91c1c}}
 .stats{{display:flex;gap:8px;flex-wrap:wrap;position:relative;z-index:1}}
 .stat{{background:rgba(255,255,255,.15);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:8px 14px;min-width:72px}}
 .stat b{{display:block;font-size:20px;font-weight:800}}
 .stat span{{font-size:10px;opacity:.8}}
 .method{{color:#475569;font-size:12px;background:linear-gradient(135deg,#eef2ff,#f0f9ff);border:1px solid #e0e7ff;border-radius:14px;padding:12px 14px;margin-bottom:16px;line-height:1.7}}
 .meta2{{color:#64748b;font-size:12px;margin-bottom:16px;text-align:center}}
 .card{{background:#fff;border:1px solid #eef0f5;border-radius:16px;padding:0;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.05);overflow:hidden;transition:box-shadow .2s,transform .2s}}
 .card:hover{{box-shadow:0 8px 28px rgba(0,0,0,.1);transform:translateY(-2px)}}
 .card-rec{{border-color:#c7d2fe;box-shadow:0 4px 20px rgba(99,102,241,.12)}}
 .hd{{display:flex;align-items:center;gap:8px;padding:14px 16px 10px;flex-wrap:wrap}}
 .nm{{font-weight:800;font-size:17px;color:#1e293b}}
 .cd{{color:#94a3b8;font-size:12px;font-family:monospace}}
 .kd{{font-size:11px;padding:2px 9px;border-radius:20px;font-weight:600}}
 .kd-黄金{{background:#fef3c7;color:#b45309}} .kd-商品{{background:#fed7aa;color:#9a3412}} .kd-跨境{{background:#dbeafe;color:#1d4ed8}} .kd-LOF{{background:#e0e7ff;color:#4338ca}}
 .idx{{font-size:11px;padding:2px 9px;border-radius:20px;font-weight:600;background:#dcfce7;color:#15803d}}
 .pr{{margin-left:auto;font-weight:800;font-size:16px}} .pr em{{font-size:12px;font-style:normal;font-weight:600}}
 .rank{{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-size:13px;padding:3px 10px;border-radius:20px;font-weight:800;min-width:32px;text-align:center}}
 .score{{color:#fff;font-size:12px;padding:3px 11px;border-radius:20px;font-weight:700}}
 .rec{{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;font-size:11px;padding:2px 9px;border-radius:20px;font-weight:700}}
 .pm-warn{{background:#fee2e2;color:#dc2626;font-size:10px;padding:1px 6px;border-radius:8px;font-weight:600}}
 .pm-ok{{background:#dcfce7;color:#16a34a;font-size:10px;padding:1px 6px;border-radius:8px;font-weight:600}}
 .bt-warn{{background:#fee2e2;color:#dc2626;font-size:10px;padding:1px 6px;border-radius:8px;font-weight:600;margin-left:6px}}
 .keybox{{display:flex;gap:1px;flex-wrap:wrap;background:#e2e8f0;margin:0 16px;border-radius:12px;overflow:hidden}}
 .kcell{{flex:1;min-width:130px;background:linear-gradient(180deg,#fff 0%,#f8fafc 100%);padding:10px 14px;text-align:center}}
 .kl{{display:block;font-size:11px;color:#94a3b8;font-weight:500;margin-bottom:3px}}
 .kv{{display:block;font-size:19px;color:#e11d48;font-weight:800;line-height:1.2}}
 .kv2{{display:block;font-size:11px;color:#94a3b8;margin-top:1px}}
 .hint{{font-size:12px;color:#64748b;margin:10px 16px;line-height:1.6;background:#f8fafc;border-radius:10px;padding:8px 10px;border:1px solid #f1f5f9}}
 .hint b{{color:#475569}}
 table.kv{{width:calc(100% - 32px);border-collapse:separate;border-spacing:0;margin:0 16px 16px;font-size:13px;border-radius:10px;overflow:hidden}}
 table.kv td{{border-bottom:1px solid #f1f5f9;padding:7px 10px}}
 table.kv tr:last-child td{{border-bottom:none}}
 table.kv td:nth-child(odd){{color:#94a3b8;background:#f8fafc;font-weight:500;width:22%}}
 table.kv td:nth-child(even){{color:#1e293b;font-weight:600}}
 svg{{display:block}}
 footer{{text-align:center;color:#94a3b8;font-size:11px;padding:20px 0 0;line-height:1.6}}
 footer b{{color:#64748b}}
 @media(max-width:600px){{.hero h1{{font-size:21px}} .nm{{font-size:15px}} .kv{{font-size:16px}} .kcell{{min-width:50%}} .pr{{font-size:14px;margin-left:0;width:100%}} }}
</style></head><body><div class="wrap">
<div class="hero">
  <h1>📊 网格交易筛选报告</h1>
  <div class="sub">生成时间：{args._now} ｜ 共选出 <b>{len(results)}</b> 只标的 ｜ 综合评分（满分100，按榜内相对水平折算：榜首≈95、榜尾60）｜ 底层因子=黏合+波动+振幅+位置+趋势</div>
  <div class="stats">
    <div class="stat"><b>{len(results)}</b><span>入选标的</span></div>
    <div class="stat"><b>{top_score:.1f}</b><span>最高评分</span></div>
    <div class="stat"><b>{avg_score:.1f}</b><span>平均评分</span></div>
    <div class="stat"><b>{prem_high}</b><span>高溢价⚠</span></div>
  </div>
</div>
{dedup_line}
{extra_html}
<div class="method">{method}</div>
<div class="meta2">均线黏合≤{args.conv}% · 近1月振幅≤{args.amp20}% · 近2月振幅≤{args.amp40}% · 年化波动≤{args.vol}% · LOF成交额≥{args.min_amount/1e4:.0f}万 · A股ETF近5日均+前一日均≥{args.min_amount_a/1e4:.0f}万 · 跨境ETF近5日均≥{MIN_AMOUNT_CROSS/1e4:.0f}万</div>
{''.join(rows)}
<footer>
  <b>⚠ 风险提示</b>：本报告由 AI 基于公开行情数据自动生成，仅供学习与研究网格交易策略，不构成任何投资建议或实盘指导。<br>
  网格交易有亏损风险，投资需谨慎。数据来源：腾讯财经 / 天天基金。<br>
  {pool_note}
</footer>
</div></body></html>"""
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
    return html


def main():
    ap = argparse.ArgumentParser(description="网格交易筛选+计算器")
    ap.add_argument("--conv", type=float, default=6.0, help="均线黏合度上限%% (默认6)")
    ap.add_argument("--amp20", type=float, default=8.0, help="近1月振幅上限%% (默认8)")
    ap.add_argument("--amp40", type=float, default=12.0, help="近2月振幅上限%% (默认12)")
    ap.add_argument("--vol", type=float, default=30.0, help="年化波动率上限%% (默认30)")
    ap.add_argument("--trend_max", type=float, default=5.0,
                    help="趋势漂移容忍%%: 近40日累计跌幅超过此值视为下跌趋势/创新低, 剔除 (默认5)")
    ap.add_argument("--box_window", type=int, default=80, help="箱体识别窗口(交易日, 默认80)")
    ap.add_argument("--box_min_days", type=int, default=20,
                    help="箱体最少震荡交易日(默认20): 上/下轨首次触及到最后触及的跨度, 太短只是短暂横盘不算箱体")
    ap.add_argument("--box_max_stale_days", type=int, default=50,
                    help="箱体最近有效性(默认50): 上/下轨聚簇成员最晚一个距今不超过X日, 超过视为旧箱体失效")
    ap.add_argument("--box_min_alternations", type=int, default=3,
                    help="箱体高-低点最低交替次数(默认3): 低-高-低-高来回切换次数不足则视为单边走势, 剔除")
    ap.add_argument("--lower_rail_stale", type=int, default=40,
                    help="下轨近期锚定窗口(默认40): 下轨以近X天(不含当天)最低 swing 低点为锚, 避免下轨被抬高")
    ap.add_argument("--upper_buffer", type=float, default=1.5,
                    help="网格上界缓冲%%(默认1.5): 网格卖出线在箱体真实上轨基础上抬高X%%, 减少上涨途中过早卖出(卖飞)")
    ap.add_argument("--box_min_grids", type=int, default=3,
                    help="箱体最少可分档数(默认3): 箱体宽度按ADR分不出这么多档就没有网格意义, 直接剔除")
    ap.add_argument("--box_tol", type=float, default=1.0,
                    help="判定宽度%%%% (默认1.0): 高点与高点(或低点与低点)价格相差不超过此幅度即视为同一水平线; 找不到2个以上会自动放宽到%.1f%%%%" % BOX_TOL_MAX)
    ap.add_argument("--bounds", choices=["box", "golden"], default="box",
                    help="上下界确定方式(默认box): box=原箱体聚簇法; golden=黄金分割法(取近 --gold_window 日最高价作顶/最低价作零, 仿通达信主力黄金线)")
    ap.add_argument("--gold_window", type=int, default=150,
                    help="黄金分割窗口(交易日, 默认150, 仿公式 HHV(HIGH,150)): 取该窗口内最高/最低价")
    ap.add_argument("--gold_lag", type=int, default=3,
                    help="黄金分割滞后(默认3, 仿公式 REF(...,3)): 排除最近N日极值干扰")
    ap.add_argument("--gold_upper", type=float, default=0.618,
                    help="黄金分割上界比例(默认0.618=六一八): 上界=零 + (顶-零)×该比例; 设1.0则取顶, 0.809取八零九")
    ap.add_argument("--gold_lower", type=float, default=0.382,
                    help="黄金分割下界比例(默认0.382=三八二): 下界=零 + (顶-零)×该比例; 设0.0则取零, 0.236取二三六")
    ap.add_argument("--gold_pressure_window", type=int, default=250,
                    help="压力位/支撑位回看窗口(默认250日): 多往前追溯, 找出人眼可见的多次触碰高点/低点")
    ap.add_argument("--gold_pressure_tol", type=float, default=5.0,
                    help="压力/支撑位修正上限%%(默认5%%): 边界最多向外修正这么多, 再远的不算")
    ap.add_argument("--gold_pressure_min_gap", type=float, default=1.0,
                    help="上界修正最小间隔%%(默认1%%): 压力位须比黄金上界高这么多才上修, 避免微调动")
    ap.add_argument("--gold_correct_near", type=float, default=4.0,
                    help="修正触发阈值%%(默认4%%): 上界只有在现价贴近它(相距<4%%)时才上修; 下界只有在存在≥4%%更深的支撑时才下修")
    ap.add_argument("--gold_bin_frac", type=float, default=0.004,
                    help="水平线聚簇分档宽度(相对价格, 默认0.004=0.4%%): 价格反复落在同一价位附近的判定宽度")
    ap.add_argument("--gold_min_touches", type=int, default=3,
                    help="水平线最少触碰次数(默认3): 同一价位至少被触碰这么多次才承认是有效压力/支撑位")
    ap.add_argument("--gold_min_ma20_cross", type=int, default=3,
                    help="黄金模式箱体确认(默认3): 近 --gold_window 日内收盘价上下穿越MA20至少这么多次才承认有箱体震荡; 否则视为单边趋势/无箱体, 剔除")
    ap.add_argument("--box_pressure_window", type=int, default=250,
                    help="箱体模式压力/支撑位回看窗口(默认250日): 找出价格反复触碰的真实高/低点, 用于把网格边界扩到真实阻力/支撑(只扩不缩)")
    ap.add_argument("--box_pressure_tol", type=float, default=5.0,
                    help="箱体模式压力/支撑修正上限%%(默认5%%): 边界最多向外扩这么多, 再远的不算")
    ap.add_argument("--box_pressure_min_gap", type=float, default=1.0,
                    help="箱体模式修正最小间隔%%(默认1%%): 须比箱体上/下轨高/低这么多才修正, 避免微调动")
    ap.add_argument("--box_bin_frac", type=float, default=0.004,
                    help="箱体模式水平线聚簇分档宽度(相对价格, 默认0.4%%): 价格反复落在同一价位附近的判定宽度")
    ap.add_argument("--box_min_touches", type=int, default=3,
                    help="箱体模式水平线最少触碰次数(默认3): 同一价位至少被触碰这么多次才承认是有效压力/支撑位")
    ap.add_argument("--ub_pct", type=float, default=85.0, help="(已弃用, 保留兼容) 上/下界现由箱体上下轨直接确定")
    ap.add_argument("--lb_pct", type=float, default=15.0, help="(已弃用, 保留兼容) 上/下界现由箱体上下轨直接确定")
    ap.add_argument("--adr_mult", type=float, default=1.0, help="间距整体微调倍数 (默认1.0=取ADR原值不调整; 如设1.2=ADR×1.2, 整体放宽)")
    ap.add_argument("--adr_window", type=int, default=20, help="计算ADR的交易日窗口(默认20=近1月)")
    ap.add_argument("--step", type=float, default=0.0, help="固定网格间距%% (0=按ADR自适应, 与--grids互斥)")
    ap.add_argument("--grids", type=int, default=0, help="固定网格档数(>=2), 优先于--step")
    ap.add_argument("--capital", type=float, default=0, help="(已弃用, 保留兼容) 报告不再输出每格金额/股数")
    ap.add_argument("--min_amount", type=float, default=20000000.0,
                    help="LOF流动性门槛: 近5日均成交额(元)下限 (默认2000万)")
    ap.add_argument("--min_amount_a", type=float, default=100000000.0,
                    help="A股ETF流动性门槛: 仅针对A股股票型ETF, 近5日均成交额(元)下限 (默认1亿); 不影响T+0默认池")
    ap.add_argument("--min_amount_ystd", type=float, default=100000000.0,
                    help="A股ETF单日流动性门槛: 仅针对A股股票型ETF, 前一日成交额(元)下限 (默认1亿)")
    ap.add_argument("--no_a_share", action="store_true",
                    help="不自动加入 股票型ETF池(默认会自动并入全市场 A股+跨境股票型 ETF, 门槛见 --min_amount_a)")
    ap.add_argument("--refresh_a_pool", action="store_true",
                    help="强制重新联网拉取 A 股 ETF 池(默认读本地缓存 a_share_etf_pool.json)")
    ap.add_argument("--pool_max_age", type=int, default=30,
                    help="全市场 ETF 名单快照允许的最大天数(默认30): 超过则先尝试联网刷新, "
                         "刷新失败会沿用旧名单并在控制台/报告里明确提示快照日期")
    ap.add_argument("--liquid_all", action="store_true",
                    help="把流动性门槛也应用到 ETF (默认仅约束 LOF)")
    ap.add_argument("--top", type=int, default=9999, help="仅展示综合评分最高的前 N 只")
    ap.add_argument("--min_results", type=int, default=10,
                    help="筛选结果至少保留 N 只; 严格筛选不足时自动逐级放宽阈值补齐(默认10, 评分很低也保留)")
    ap.add_argument("--no_fill", action="store_true",
                    help="关闭'不足N只自动放宽'兜底, 仅输出严格达标标的")
    ap.add_argument("--max_results", type=int, default=15,
                    help="筛选结果最多保留 N 只(默认15); 配合 --min_results 把最终标的控制在 [min,max] 区间(默认10-15只), 避免同指数重复+数量过多")
    ap.add_argument("--no_dedup", action="store_true",
                    help="关闭'同指数去重': 默认同一跟踪指数/主题只留评分最高一只, 关掉则保留全部入选标的")
    ap.add_argument("--max_premium", type=float, default=10.0,
                    help="高溢价硬过滤阈值%%(默认10): 跨境/LOF ETF 溢价率超过此值直接剔除(网格按交易价设, 溢价回落会额外亏损); 设很大(如999)即关闭")
    ap.add_argument("--no_premium_filter", action="store_true",
                    help="关闭'高溢价硬过滤': 默认剔除溢价率>--max_premium%%的跨境/LOF ETF")
    ap.add_argument("--universe", type=str, default="", help="自定义标的池 CSV (列: code,name,kind)")
    ap.add_argument("--out", type=str, default=".", help="输出目录 (默认当前)")
    ap.add_argument("--datalen", type=int, default=500, help="获取的日K数量 (默认500, 需覆盖箱体识别窗口)")
    args = ap.parse_args()
    if args.no_premium_filter:
        args.max_premium = 1e9   # 关闭高溢价硬过滤
    args._now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")

    uni = load_universe(args.universe)
    if not args.no_a_share and not args.universe:
        a_pool = fetch_a_share_etf_codes(refresh=args.refresh_a_pool,
                                         max_age_days=args.pool_max_age)
        if a_pool:
            seen_codes = {c[0] for c in uni}
            a_pool = [c for c in a_pool if c[0] not in seen_codes]
            uni = list(uni) + a_pool
            print(f"(已自动并入 股票型ETF池: A股 {sum(1 for c in a_pool if c[2]=='A股ETF')} 只(近5日均+前一日均≥1亿) + 跨境 {sum(1 for c in a_pool if c[2]=='跨境A')} 只(近5日均≥5000万), 原本T+0默认池标准不变)\n")
        # v1.0.32: 全市场名单快照新鲜度提示——宁可明说, 绝不静默用旧名单
        pm = A_POOL_META
        if pm.get("date"):
            if pm.get("stale") and pm.get("refresh_failed"):
                print(f"⚠ 全市场 ETF 名单快照生成于 {pm['date']}（已 {pm['age_days']} 天），"
                      f"超过 {args.pool_max_age} 天未更新且联网刷新失败。")
                print(f"  本次沿用该旧名单，可能缺少此后新上市的 ETF。"
                      f"若网络正常，稍后可加 --refresh_a_pool 强制更新。\n")
            elif pm.get("stale"):
                print(f"(全市场名单快照生成于 {pm['date']}，已 {pm['age_days']} 天)\n")
            else:
                print(f"(全市场名单快照生成于 {pm['date']}，{pm['age_days']} 天内，较新)\n")
        elif not a_pool:
            print("⚠ 未能获取全市场 ETF 名单（无本地快照且联网拉取失败），"
                  "本次仅扫描内置的 96 只 T+0 标的池，A 股 ETF 不会被纳入。\n")
    print(f"标的池: {len(uni)} 只, 开始抓取行情并计算指标...\n")

    def work(item):
        code, name, kind = item
        k = fetch_kline(code, args.datalen)
        if not k:
            return code, None, "无行情数据"
        c, reason = evaluate(code, name, kind, k, args)
        return code, c, reason

    candidates = []          # 通过"硬安全过滤"且已算好全部指标的候选
    reasons = {}             # 硬失败原因(无行情/数据不足/通道异常)
    with ThreadPoolExecutor(max_workers=8) as ex:
        for code, cand, reason in ex.map(work, uni):
            if cand:
                candidates.append(cand)
            else:
                reasons[code] = reason

    # ---- 同指数/主题去重: 同一跟踪指数只留评分最高一只, 避免大量重复跟踪同一指数的标的 ----
    dedup_n, dedup_details = 0, []
    if not args.no_dedup:
        candidates, dedup_n, dedup_details = dedup_by_index(candidates, args)
        if dedup_n:
            print(f"(同指数去重: 合并掉 {dedup_n} 只同标的次优ETF, 各指数仅留评分最高一只)\n")

    # ---- 数量兜底: 保证结果不少于 --min_results 只(评分很低也保留) ----
    # ---- 溢价率预取(用于"高溢价硬过滤" + 报告展示): 对去重后全部候选取净值算溢价率 ----
    # 放在放宽入选之前, 使 passes() 能按溢价剔除异常高溢价的跨境/LOF(网格按交易价设, 溢价回落会额外亏损)。
    # 取不到净值(premium=None)的标的保守保留, 不误杀。
    def fill_nav(c):
        nav, nav_date = fetch_nav(c["code"])
        c["nav"] = nav
        c["nav_date"] = nav_date
        c["premium"] = (c["cur"] / nav - 1) * 100.0 if nav else None
        return c
    if candidates:
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(fill_nav, candidates))

    premium_excluded = sum(1 for c in candidates
                           if c.get("premium") is not None and c["premium"] > args.max_premium)
    if premium_excluded:
        print(f"(高溢价硬过滤: 剔除 {premium_excluded} 只溢价>{args.max_premium:.0f}% 的跨境/LOF ETF, "
              f"网格按交易价设置, 溢价回落后会额外亏损)\n")

    strict_n = sum(1 for c in candidates if passes(c, args, STAGES[0])[0])
    selected, stage_used = relax_select(candidates, args, 0 if args.no_fill else args.min_results)
    if args.no_fill:
        fillnote = f"已关闭数量兜底, 仅输出严格达标 {len(selected)} 只"
    elif selected and stage_used > 0:
        fill_n = len(selected) - strict_n
        fillnote = (f"严格达标仅 {strict_n} 只, 不足 --min_results={args.min_results}; "
                    f"已自动逐级放宽阈值至第 {stage_used} 档补齐 {max(fill_n, 0)} 只, "
                    f"最终 {len(selected)} 只(放宽标的评分偏低, 质量需自行权衡)")
    elif selected and strict_n >= args.min_results:
        fillnote = f"严格即达标 {strict_n} 只, 无需放宽"
    elif selected:
        fillnote = f"严格达标 {strict_n} 只, 已含全部可达标标的(即便放宽各档仍不足 {args.min_results})"
    else:
        fillnote = "未选出任何标的"

    # 注: 溢价率已在上方对全部候选预取(用于硬过滤), 此处不再重复取。

    # 按综合评分降序(分数越高越适合做网格)
    selected.sort(key=lambda r: r["score"], reverse=True)
    results = selected[:min(args.top, args.max_results)]

    # v1.0.39: 评分展示改为"榜内满分制"——把榜内原始分线性折算到 [60, 95]:
    # 榜首≈95分、榜尾60分, 学员看到的就是常规"满分100"的心智模型。
    # 排序/去重/兜底等所有筛选逻辑仍用原始 score, 此处仅影响展示。
    if results:
        _smin = min(r["score"] for r in results)
        _smax = max(r["score"] for r in results)
        if _smax - _smin < 1e-9:
            for r in results:
                r["score_disp"] = 80.0
        else:
            for r in results:
                r["score_disp"] = round(60.0 + (r["score"] - _smin) / (_smax - _smin) * 35.0, 1)

    os.makedirs(args.out, exist_ok=True)
    # CSV
    csv_path = os.path.join(args.out, "grid_results.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["排名", "代码", "名称", "类别", "综合评分", "日期", "当前价", "涨跌幅%", "趋势漂移%",
                    "均线黏合度%", "近1月振幅%", "近2月振幅%", "年化波动%", "溢价率%", "上界", "下界",
                    "中枢(基准价)", "网格间距%", "网格间距(元)", "网格档数", "当前档", "净值日期",
                    "日均波幅ADR%", "近5日均成交额(估算)", "前一日成交额(估算)", "箱体有效跨度天数",
                    "上轨碰线次数", "上轨附近高点", "下轨碰线次数", "下轨附近低点", "判定宽度%",
                    "区间方式", "区间基准高位(近W日最高)", "区间基准低位(近W日最低)", "跟踪指数/主题"])
        for i, r in enumerate(results, 1):
            w.writerow([i, r["code"], r["name"], r["kind"].replace("跨境A", "跨境"), f"{r['score_disp']:.1f}",
                        r["date"], fmt(r["cur"]), fmt(r["chg"], 1), fmt(r["drift"], 1), fmt(r["conv"], 1),
                        fmt(r["amp20"], 1), fmt(r["amp40"], 1), fmt(r["ann_vol"], 1),
                        (f"{r['premium']:+.2f}" if r["premium"] is not None else ""),
                        fmt(r["upper"]), fmt(r["lower"]), fmt(r["center"]),
                        fmt(r["step_pct"], 1), fmt(r["step_price"]),
                        r["grids"], r["level"], (r["nav_date"] or ""),
                        fmt(r["adr"], 1),
                        f"{r['amount_5d']:.0f}",
                        f"{r['amount_1d']:.0f}",
                        r["box_days"], r["box_touch_hi"], r["box_hits_hi"],
                        r["box_touch_lo"], r["box_hits_lo"], f"{r['box_tol']:.1f}",
                        r["bounds_mode"], fmt(r["_box_high"]), fmt(r["_box_low"]),
                        (r.get("index_key") or "")])

    # HTML
    dedup_line = ""
    if dedup_n:
        dedup_line = (f'<div class="dedup-note">✅ 已按跟踪指数/主题去重：合并掉 <b>{dedup_n}</b> 只同指数次优 ETF'
                      f'（涉及 {len(dedup_details)} 个指数/主题），各指数仅保留评分最高 1 只，最终 <b>{len(results)}</b> 只。</div>')
    html_path = os.path.join(args.out, "grid_report.html")
    render_html(results, args, html_path, fillnote, dedup_line=dedup_line)

    # 控制台摘要
    data_issues = {c: r for c, r in reasons.items() if ("行情" in r or "数据" in r)}
    relax_fail = len(candidates) - len(selected)  # 即便放宽各档仍不达标(突破箱体/下跌趋势等)
    print(f"扫描 {len(uni)} 只, 候选(过硬过滤) {len(candidates)} 只, 最终选中 {len(results)} 只")
    if dedup_n:
        _det = "; ".join(f"{b}←{'/'.join(d)}" for b, d in dedup_details)
        print(f"同指数去重合并 {dedup_n} 只(保留→合并掉的): {_det}\n")
    # 不打印兜底说明（min_results 默认仍生效，保证结果不低于 --min_results 只）
    if data_issues:
        print(f"数据缺失/无行情(可清理的代码): {', '.join(data_issues)}\n")
    if relax_fail > 0:
        print(f"另有 {relax_fail} 只即便放宽各档仍不达标(突破箱体上沿/下跌趋势创新低/通道异常等), 已排除。\n")
    if results:
        print(f"{'排名':>4}{'代码':<8}{'名称':<12}{'评分':>6}{'黏合%':>7}{'漂移%':>7}{'1月幅%':>8}{'上界':>9}{'下界':>9}{'间距%':>7}{'档':>4}{'溢%':>7}")
        for i, r in enumerate(results, 1):
            prem_cell = f"{r['premium']:+.1f}" if r['premium'] is not None else "—"
            print(f"{i:>4}{r['code']:<8}{r['name']:<12}{r['score_disp']:>6.1f}"
                  f"{fmt(r['conv'],1):>7}{fmt(r['drift'],1):>7}{fmt(r['amp20'],1):>8}"
                  f"{fmt(r['upper']):>9}{fmt(r['lower']):>9}{fmt(r['step_pct'],1):>7}{r['grids']:>4}"
                  f"{prem_cell:>7}")
    if args.bounds == "golden":
        print(f"\n区间判定: 取近{args.gold_window}日最高价作「顶」、最低价作「零」(不含最近{args.gold_lag}日), "
              f"上/下界由黄金分割比例{args.gold_upper:.3f}/{args.gold_lower:.3f}决定(默认六一八/三八二); "
              f"再回看近{args.gold_pressure_window}日反复触碰的压力/支撑位做修正(现价贴近上界时上修到压力位、存在更深支撑时下修到支撑位)。"
              f"当前价必须落在顶/零之间, 且未进入明显下跌趋势。"
              f"间距默认取日均波幅×0.7(保底1%, 每只不同, 即填入APP的网格间距). "
              f"用 --gold_window/--gold_lag 调整高低点回看窗口, --gold_upper/--gold_lower 调整分割比例; "
              f"--step/--grids 可固定间距/档数, --adr_mult 回到老口径(ADR×倍数, 不足1%取1%).")
    else:
        print(f"\n箱体判定: 近{args.box_window}日内需至少两个高点价格接近(判定宽度{args.box_tol}%)连成上轨、两个低点连成下轨; "
              f"且当前价仍在箱体内; 上/下界=箱体上/下轨触及价. "
              f"间距默认取日均波幅×0.7(保底1%, 每只不同, 即填入APP的网格间距). "
              f"用 --box_window/--box_tol 调箱体口径, --step/--grids 可固定间距/档数, --adr_mult 回到老口径(ADR×倍数, 不足1%取1%).")
    print(f"\n已生成:\n  CSV : {csv_path}\n  HTML: {html_path}")
    if not results:
        print(f"\n未选出任何标的, 可放宽阈值 (如 --conv 8 --amp20 10 --amp40 15) 或关闭数量兜底(--no_fill) 再试。")


if __name__ == "__main__":
    main()
