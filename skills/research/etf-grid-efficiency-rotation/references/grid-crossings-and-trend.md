# Grid Crossings and Trend Ratio — Implementation Notes

## Why max/min range is wrong

`max(closes) / min(closes) - 1` only captures the extreme high and low over a window. It loses all information about **how many times** price oscillated between them.

Example — same range_pct, completely different grid suitability:

| Path | closes | range_pct | grid crossings |
|---|---|---|---|
| Repeated swing | 1.00, 1.03, 1.00, 1.03, 1.00, 1.03 | 3.0% | **6** |
| Single spike | 1.00, 1.045, 1.00, 1.00, 1.00, 1.00 | 4.5% | **2** |

The first path is genuinely grid-friendly (price crosses the 2% spacing repeatedly). The second is a one-off spike — the grid would fire once and then sit idle.

## Grid crossings algorithm

```python
def count_grid_crossings(closes, gap=0.02):
    if len(closes) < 2:
        return 0
    crossings = 0
    level = closes[0]
    for p in closes[1:]:
        if p >= level * (1 + gap):
            crossings += 1
            level = p
        elif p <= level / (1 + gap):
            crossings += 1
            level = p
    return crossings
```

Key property: after each crossing, the reference level jumps to the new price. This means a sustained drift in one direction counts as one crossing (not many), while repeated oscillations count as many.

## Trend ratio

```python
def recent_trend_ratio(closes, lookback=10):
    if len(closes) < lookback + 5:
        return None
    ma20 = sum(closes[-20:]) / 20
    recent = closes[-lookback:]
    above = sum(1 for p in recent if p > ma20)
    return round(above / len(recent), 3)
```

- > 0.6 → uptrend
- < 0.4 → downtrend
- 0.4–0.6 → range

This is more robust than comparing first vs last close because it uses the full recent window against a moving average, not just two points.

## How they feed into assess_low_efficiency

```
if crossings <= 1:
    → "price has not covered the grid spacing; genuine low volatility"
elif cycles_10d == 0:
    → "no completed cycles recently; crossings exist but grid isn't working"
else:
    → "crossings exist, cycles are sparse; likely trend, not low volatility"
```

The completed-cycle count (`completed_cycles` from the ledger) remains the primary signal. Crossings and trend ratio explain **why** cycles are low.

## Implementation

Production code: `scripts/grid_rotation_review.py`
Tests: `scripts/test_grid_rotation_review.py`

See the `etf-grid-efficiency-rotation` SKILL.md for the class-level workflow.
