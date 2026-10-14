# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import grid_rotation_review as review
import grid_eod_decision as eod
import grid_weekly_rotation as weekly


class RotationReviewTests(unittest.TestCase):
    def test_completed_cycles_pairs_only_confirmed_buy_then_sell(self):
        book = {
            "history": [
                {"date": "2026-09-01", "result": "成功", "actions": [
                    {"code": "sz159363", "side": "buy", "lot": "D", "qty": 5100, "price": 1.169}
                ]},
                {"date": "2026-09-02", "result": "成功", "actions": [
                    {"code": "sz159363", "side": "sell", "lot": "D", "qty": 5100, "price": 1.192}
                ]},
                {"date": "2026-09-03", "result": "成功", "actions": [
                    {"code": "sz159363", "side": "sell", "lot": "C", "qty": 4800, "price": 1.221}
                ]},
            ]
        }
        rows = review.completed_cycles(book, "sz159363", date(2026, 8, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lot"], "D")

    def test_low_efficiency_needs_a_full_observation_window(self):
        day = date(2026, 9, 30)
        bars = [{"date": (day - timedelta(days=2 * i)).isoformat(), "close": 1.0} for i in range(10)]
        result = review.assess_low_efficiency([], bars, day)
        self.assertEqual(result["state"], "DATA_INSUFFICIENT")

    def test_narrow_range_with_one_cycle_is_low_efficiency(self):
        day = date(2026, 9, 30)
        bars = [{"date": (day - timedelta(days=i)).isoformat(), "close": 1.000 + (i % 2) * 0.005} for i in range(20)]
        cycles = [{"sell_date": "2026-09-20"}]
        result = review.assess_low_efficiency(cycles, bars, day)
        self.assertEqual(result["state"], "LOW_EFFICIENCY")
        self.assertEqual(result["cycles_20d"], 1)
        self.assertLessEqual(result["crossings"], 1)

    def test_repeated_oscillation_counts_more_crossings_than_single_spike(self):
        day = date(2026, 9, 30)
        spike = [{"date": (day - timedelta(days=i)).isoformat(),
                  "close": 1.000 if i % 2 == 0 else 1.010} for i in range(20)]
        swing = [{"date": (day - timedelta(days=i)).isoformat(),
                  "close": 1.000 if i % 2 == 0 else 1.030} for i in range(20)]
        spike_cross = review.count_grid_crossings([x["close"] for x in spike])
        swing_cross = review.count_grid_crossings([x["close"] for x in swing])
        self.assertGreater(swing_cross, spike_cross)

    def test_trend_ratio_distinguishes_uptrend_from_range(self):
        day = date(2026, 9, 30)
        flat = [{"date": (day - timedelta(days=i)).isoformat(), "close": 1.0} for i in range(20)]
        rising = [{"date": (day - timedelta(days=i)).isoformat(),
                   "close": 1.0 + i * 0.002} for i in range(20)]
        self.assertEqual(review.recent_trend_ratio([x["close"] for x in flat]), 0.0)
        self.assertGreater(review.recent_trend_ratio([x["close"] for x in rising]) or 0, 0.6)

    def test_low_efficiency_uses_crossings_not_max_min_range(self):
        day = date(2026, 9, 30)
        spike = [{"date": (day - timedelta(days=i)).isoformat(),
                  "close": 1.000 if i % 2 == 0 else 1.045} for i in range(20)]
        cycles = [{"sell_date": "2026-09-20"}]
        result = review.assess_low_efficiency(cycles, spike, day)
        self.assertEqual(result["state"], "LOW_EFFICIENCY")
        self.assertIn("网格穿越", result["reason"])

    def test_weekly_switch_signal_requires_same_peer_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder) / "state.json"
            comparison = {"baseline": 4, "leader": "sh000001", "leader_cycles": 7, "window_sessions": 63}
            first = review.update_consecutive_signal(state_path, comparison, date(2026, 9, 25))
            second = review.update_consecutive_signal(state_path, comparison, date(2026, 10, 2))
        self.assertFalse(first["switch_review_due"])
        self.assertTrue(second["switch_review_due"])
        self.assertEqual(second["consecutive_weeks"], 2)

    def test_weekly_signal_resets_when_leader_changes_or_same_day_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder) / "state.json"
            first = {"baseline": 4, "leader": "sh000001", "leader_cycles": 6}
            review.update_consecutive_signal(state_path, first, date(2026, 9, 25))
            same = review.update_consecutive_signal(state_path, first, date(2026, 9, 25))
            self.assertEqual(same["consecutive_weeks"], 1)
            other = review.update_consecutive_signal(state_path, {**first, "leader": "sh000002"}, date(2026, 10, 2))
            self.assertEqual(other["consecutive_weeks"], 1)

    def test_daily_eod_favors_rotation_over_old_uptrend_rebase(self):
        day = date(2026, 9, 29)
        bars = [{"date": (day - timedelta(days=30-i)).isoformat(), "close": 0.85}
                for i in range(31)]
        book = {"opened": "2026-09-23", "history": [],
                "positions": {"sz159992": {"qty": 10000, "rebuy": [], "lots": []}}}
        result = eod.assess("sz159992", book, bars, day)
        self.assertNotEqual(result["state"], "REVIEW_REBASE")
        self.assertFalse(result["executable"])

    def test_weekly_comparison_rejects_missing_current_data(self):
        base = [{"date": f"2026-08-{i:02d}", "close": 1.0} for i in range(1, 21)]
        with self.assertRaises(ValueError):
            review.compare_close_proxy({"baseline": base}, "baseline", [], date(2026, 9, 30))

    def test_weekly_comparison_counts_same_window_and_switch_is_review_only(self):
        day = date(2026, 9, 30)
        dates = [(day - timedelta(days=i)).isoformat() for i in range(63)][::-1]
        flat = [{"date": d, "close": 1.0 + (0.03 if i % 2 else 0.0)} for i, d in enumerate(dates)]
        moving = [{"date": d, "close": 1.0 + (0.03 if i % 2 else 0.0) + i * 0.0005} for i, d in enumerate(dates)]
        result = review.compare_close_proxy({"baseline": flat, "candidate": moving},
                                            "baseline", ["candidate"], day)
        self.assertEqual(result["window_sessions"], 63)
        self.assertEqual(result["leader"], "candidate")
        self.assertGreater(result["baseline"], 0)
        self.assertIn("compared_net", result)
        self.assertIn("method", result)

    def test_cross_theme_outranker_when_same_theme_fails(self):
        day = date(2026, 9, 30)
        dates = [(day - timedelta(days=i)).isoformat() for i in range(63)][::-1]
        flat = [{"date": d, "close": 1.0} for d in dates]
        moving = [{"date": d, "close": (0.97 if i % 2 else 1.0)} for i, d in enumerate(dates)]
        screened = weekly.compare_themes(
            {"sh589720": flat, "sh589120": flat, "sh515220": moving}, day,
            {"创新药": ["sh589720", "sh589120"], "煤炭": ["sh515220"]},
        )
        self.assertIsNone(screened["same_theme"]["leader"])
        self.assertEqual(screened["cross_theme"]["leader"], "sh515220")
        self.assertEqual(screened["cross_theme"]["leader_theme"], "煤炭")
        self.assertFalse(screened["cross_theme"]["executable"])

    def test_cross_theme_equal_or_missing_data_is_not_a_switch_signal(self):
        day = date(2026, 9, 30)
        dates = [(day - timedelta(days=i)).isoformat() for i in range(63)][::-1]
        flat = [{"date": d, "close": 1.0} for d in dates]
        screened = weekly.compare_themes(
            {"sh589720": flat, "sh515220": flat}, day,
            {"创新药": ["sh589720"], "煤炭": ["sh515220"], "有色": ["sh560860"]},
        )
        self.assertIsNone(screened["cross_theme"]["leader"])
        self.assertIn("sh560860", screened["cross_theme"]["missing"])

    def test_cross_theme_candidate_needs_two_weekly_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "cross-theme-state.json"
            comparison = {"baseline": 1, "leader": "sh515220", "leader_cycles": 3, "window_sessions": 63}
            first = review.update_consecutive_signal(state, comparison, date(2026, 9, 25))
            second = review.update_consecutive_signal(state, comparison, date(2026, 10, 2))
            self.assertFalse(first["switch_review_due"])
            self.assertTrue(second["switch_review_due"])
    def test_cross_theme_gap_week_resets_consecutive_counter(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "cross-theme-state.json"
            comparison = {"baseline": 1, "leader": "sh515220", "leader_cycles": 3}
            review.update_consecutive_signal(state, comparison, date(2026, 9, 25))
            after_gap = review.update_consecutive_signal(state, comparison, date(2026, 10, 16))
            self.assertEqual(after_gap["consecutive_weeks"], 1)
            self.assertFalse(after_gap["switch_review_due"])

    def test_weekly_report_includes_cross_theme_and_keeps_migration_read_only(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo
        day = date(2026, 9, 30)
        dates = [(day - timedelta(days=i)).isoformat() for i in range(63)][::-1]
        flat = [{"date": d, "close": 1.0 + (0.03 if i % 2 else 0.0)} for i, d in enumerate(dates)]
        moving = [{"date": d, "close": 1.0 + (0.03 if i % 2 else 0.0) + i * 0.0005} for i, d in enumerate(dates)]
        bars = {code: flat for codes in weekly.THEMES.values() for code in codes}
        bars["sh515220"] = moving
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(weekly, "ROTATION", Path(folder)), \
             patch.object(weekly, "STATE", Path(folder) / "same.json"), \
             patch.object(weekly, "CROSS_STATE", Path(folder) / "cross.json"), \
             patch.object(weekly, "migration_policy", return_value={"target": weekly.BASELINE}), \
             patch.object(weekly, "fetch_daily", side_effect=lambda code: bars[code]):
            text = weekly.main(datetime(2026, 9, 30, 15, 25, tzinfo=ZoneInfo("Asia/Shanghai")))
            report = json.loads((Path(folder) / "2026-09-30.json").read_text(encoding="utf-8"))
            self.assertEqual(report["cross_theme"]["leader"], "sh515220")
            self.assertIn("跨题材轮换观察", text)
            self.assertIn("159992→589720", text)
            self.assertIn("不自动买入", text)
            self.assertIn("净差价", text)


if __name__ == "__main__":
    unittest.main()
