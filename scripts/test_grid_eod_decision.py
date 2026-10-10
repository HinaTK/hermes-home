# -*- coding: utf-8 -*-
"""Evening-only advisory never changes grid tickets or broker orders."""
import unittest
from datetime import date, timedelta

import grid_eod_decision as eod


class EveningDecisionTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        policy = patch.object(eod, "migration_policy", return_value=None)
        policy.start()
        self.addCleanup(policy.stop)
        self.day = date(2026, 9, 29)
        start = self.day - timedelta(days=39)
        self.bars = [{"date": (start + timedelta(days=i)).isoformat(), "close": round(0.85 + i * 0.004, 3)} for i in range(40)]
        self.last = self.bars[-1]["close"]
        self.book = {"history": [{"date": "2026-09-20", "result": "成功", "actions": [
            {"code": "sz159992", "side": "sell", "qty": 9400, "price": 0.88}
        ]}], "positions": {"sz159992": {"qty": 0, "rebuy": [], "lots": []}}}

    def test_persistent_rise_and_low_inventory_is_review_only(self):
        result = eod.assess("sz159992", self.book, self.bars, self.day)
        self.assertEqual(result["state"], "ROTATION_REVIEW")
        self.assertFalse(result["executable"])
        self.assertEqual(result["efficiency"]["cycles_20d"], 0)

    def test_recent_rebuy_disables_rebase(self):
        self.book["history"].append({"date": "2026-09-29", "result": "成功", "actions": [
            {"code": "sz159992", "side": "buy", "qty": 9400, "price": 0.88}
        ]})
        self.assertNotEqual(eod.assess("sz159992", self.book, self.bars, self.day)["state"], "REVIEW_REBASE")

    def test_active_inventory_is_not_chased(self):
        self.book["positions"]["sz159992"]["qty"] = 27700
        self.assertEqual(eod.assess("sz159992", self.book, self.bars, self.day)["state"], "ROTATION_REVIEW")

    def test_first_close_above_sale_triggers_early_review_with_core(self):
        self.book["history"][0]["actions"][0]["price"] = 0.985
        self.book["positions"]["sz159992"]["qty"] = 9100
        self.assertLess(self.bars[-2]["close"], 0.985 * 1.02)
        result = eod.assess("sz159992", self.book, self.bars, self.day)
        self.assertEqual(result["state"], "ROTATION_REVIEW")
        self.assertFalse(result["executable"])

    def test_outstanding_rebuy_allows_review_but_does_not_cancel_order(self):
        self.book["positions"]["sz159992"]["qty"] = 9100
        self.book["positions"]["sz159992"]["rebuy"] = [{"qty": 9400, "price": 0.863}]
        result = eod.assess("sz159992", self.book, self.bars, self.day)
        self.assertEqual(result["state"], "ROTATION_REVIEW")
        self.assertIn("效率预警", result["reason"])
        self.assertEqual(self.book["positions"]["sz159992"]["rebuy"], [{"qty": 9400, "price": 0.863}])

    def test_incomplete_day_is_rejected(self):
        with self.assertRaises(ValueError):
            eod.assess("sz159992", self.book, self.bars[:-1], self.day)

    def test_old_policy_report_is_not_attached_to_morning_ticket(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import grid_weixin_ops
        with tempfile.TemporaryDirectory() as folder, patch.object(eod, "STORE", Path(folder)):
            report = {"for_session": "2026-09-30", "history_count": 0,
                      "decisions": {"sz159992": {"state": "REVIEW_REBASE", "watch_price": 0.94}}}
            (Path(folder) / "2026-09-29.json").write_text(json.dumps(report), encoding="utf-8")
            with patch.object(grid_weixin_ops, "load", return_value={"history": []}):
                text = grid_weixin_ops.with_evening_review("原操作单", date(2026, 9, 30), "preview")
            self.assertIn("旧版评估已失效", text)
            self.assertNotIn("观察回踩价", text)

    def test_morning_note_reads_only_matching_evening_report(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import grid_weixin_ops
        with tempfile.TemporaryDirectory() as folder, patch.object(eod, "STORE", Path(folder)):
            report = {"for_session": "2026-09-30", "policy_version": eod.POLICY_VERSION, "decisions": {"sz159992": {
                "state": "REVIEW_REBASE", "watch_price": 0.94, "reason": "testing"}}}
            (Path(folder) / "2026-09-29.json").write_text(json.dumps(report), encoding="utf-8")
            text = grid_weixin_ops.with_evening_review("原操作单", date(2026, 9, 30), "execute")
            self.assertIn("原操作单", text)
            self.assertIn("勿按候选价下单", text)
            self.assertEqual(grid_weixin_ops.with_evening_review("原操作单", date(2026, 10, 8), "preview"), "原操作单")

    def test_morning_note_suppresses_stale_after_fill(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import grid_weixin_ops
        with tempfile.TemporaryDirectory() as folder, patch.object(eod, "STORE", Path(folder)):
            report = {"for_session": "2026-09-30", "policy_version": eod.POLICY_VERSION, "history_count": 2,
                      "decisions": {"sz159992": {"state": "REVIEW_REBASE", "watch_price": 0.94}}}
            (Path(folder) / "2026-09-29.json").write_text(json.dumps(report), encoding="utf-8")
            with patch.object(grid_weixin_ops, "load", return_value={"history": [1, 2, 3]}):
                self.assertIn("昨收评估已失效", grid_weixin_ops.with_evening_review("原操作单", date(2026, 9, 30), "execute"))
                self.assertNotIn("观察回踩价", grid_weixin_ops.with_evening_review("原操作单", date(2026, 9, 30), "execute"))

    def test_close_run_writes_dated_report_without_changing_ledger(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from datetime import datetime
        from zoneinfo import ZoneInfo
        b = {"history": list(self.book["history"]), "positions": {
            "sz159992": self.book["positions"]["sz159992"],
            "sz159363": {"qty": 14000, "rebuy": [], "lots": []}}}
        before = json.dumps(b, sort_keys=True)
        quotes = {code: {"last": str(self.last), "time": "20260929150500"} for code in ("sz159992", "sz159363")}
        with tempfile.TemporaryDirectory() as folder, patch.object(eod, "STORE", Path(folder)), \
             patch.object(eod, "fetch_quotes", return_value=quotes), \
             patch.object(eod, "fetch_daily", return_value=self.bars), \
             patch.object(eod, "load", return_value=b):
            text = eod.main(datetime(2026, 9, 29, 15, 20, tzinfo=ZoneInfo("Asia/Shanghai")))
            saved = json.loads((Path(folder) / "2026-09-29.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["for_session"], "2026-09-30")
            self.assertEqual(saved["history_count"], 1)
            self.assertIn("勿按候选价下单", text)
            self.assertEqual(json.dumps(b, sort_keys=True), before)

    def test_preview_is_non_executable(self):
        result = {"for_session": "2026-09-30", "decisions": {"sz159992": {"state": "REVIEW_REBASE", "watch_price": 0.94}}}
        text = eod.next_day_note(result, date(2026, 9, 30), "execute")
        self.assertIn("仅供复核", text)
        self.assertIn("勿按候选价下单", text)
        self.assertEqual(eod.next_day_note(result, date(2026, 10, 8), "preview"), "")

    def test_cleanup_clears_unconfirmed_buy_orders(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(eod, "ROOT", Path(folder)), \
             patch.object(eod, "migration_policy", return_value={"historical_unconfirmed_buy_orders": [{"code": "sz159992", "qty": 9400, "price": 0.846}]}):
            book = {"positions": {}}
            changed = eod.cleanup_after_close(book)
            self.assertTrue(changed)
            saved = json.loads((Path(folder) / "migration.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["historical_unconfirmed_buy_orders"], [])

    def test_cleanup_removes_zero_qty_rebuy(self):
        from unittest.mock import patch
        with patch.object(eod, "migration_policy", return_value=None):
            book = {"positions": {"sz159992": {"rebuy": [{"qty": 0, "price": 0.846}, {"qty": 9400, "price": 0.863}]}}}
            changed = eod.cleanup_after_close(book)
            self.assertTrue(changed)
            self.assertEqual(len(book["positions"]["sz159992"]["rebuy"]), 1)
            self.assertEqual(book["positions"]["sz159992"]["rebuy"][0]["qty"], 9400)

    def test_cleanup_no_change_when_nothing_to_clean(self):
        from unittest.mock import patch
        with patch.object(eod, "migration_policy", return_value=None):
            book = {"positions": {"sz159992": {"rebuy": [{"qty": 9400, "price": 0.863}]}}}
            changed = eod.cleanup_after_close(book)
            self.assertFalse(changed)

    def test_cleanup_handles_none_policy(self):
        from unittest.mock import patch
        with patch.object(eod, "migration_policy", return_value=None):
            book = {"positions": {}}
            changed = eod.cleanup_after_close(book)
            self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
