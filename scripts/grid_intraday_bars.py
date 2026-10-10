# -*- coding: utf-8 -*-
"""Tencent one-minute OHLC for grid observation, not broker fill evidence."""
from __future__ import annotations

import json
import urllib.request

URL = "https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m1,,80"


def parse_rows(rows):
    bars = []
    for row in rows:
        if len(row) < 6:
            continue
        stamp = str(row[0])
        if len(stamp) != 12 or not stamp.isdigit():
            continue
        try:
            high, low, volume = float(row[3]), float(row[4]), float(row[5])
        except (TypeError, ValueError):
            continue
        if volume <= 0 or low <= 0 or high < low:
            continue
        bars.append({"time": stamp, "high": high, "low": low})
    return bars


def fetch_minute_bars(codes):
    result = {}
    for code in codes:
        request = urllib.request.Request(URL.format(code=code), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.load(response)
        if payload.get("code") != 0:
            raise ValueError(f"{code} minute API returned {payload.get('code')}")
        result[code] = parse_rows(payload.get("data", {}).get(code, {}).get("m1", []))
    return result
