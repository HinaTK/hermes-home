# -*- coding: utf-8 -*-
"""Feishu script stdout checks, never publishes or touches the real ledger."""
import io
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from unittest.mock import patch

import grid_weixin_ops as ops
import test_grid_migration as fixtures


class NotificationTests(unittest.TestCase):
    def test_forced_execute_is_silent_on_market_holiday_without_loading_or_fetching(self):
        with patch.object(ops, "datetime") as clock, \
             patch.object(ops.sys, "argv", ["grid_weixin_execute.py", "--phase", "execute"]), \
             patch.object(ops, "load", return_value={}) as load, \
             patch.object(ops, "fetch_quotes", return_value=None) as quotes:
            clock.now.return_value = datetime(2026, 10, 1, 9, 31, tzinfo=ops.TZ)
            out = io.StringIO()
            with redirect_stdout(out):
                ops.main()
            self.assertEqual(out.getvalue(), "")
            load.assert_not_called()
            quotes.assert_not_called()


class FeishuMigrationFlowTests(unittest.TestCase):
    def setUp(self):
        fixtures.MigrationTests.setUp(self)

    def test_opening_script_outputs_exit_only_and_reconciliation_without_target_buy(self):
        day = date(2026, 10, 8)
        quotes = {code: dict(q, time="20261008093100") for code, q in self.quotes.items()}
        with patch.object(ops, "datetime") as clock, \
             patch.object(ops.sys, "argv", ["grid_weixin_execute.py", "--phase", "execute"]), \
             patch.object(ops, "today", return_value=day), \
             patch.object(ops, "load", return_value=self.book), \
             patch.object(ops, "fetch_quotes", return_value=quotes), \
             patch.object(ops, "with_evening_review", side_effect=lambda text, *_: text):
            clock.now.return_value = datetime(2026, 10, 8, 9, 31, tzinfo=ops.TZ)
            out = io.StringIO()
            with redirect_stdout(out):
                ops.main()
        text = out.getvalue()
        self.assertIn("停止新增买入和接回", text)
        self.assertIn("本地停买不代表已撤单", text)
        self.assertIn("当前不挂589720买单", text)
        self.assertIn("卖 B 格", text)
        self.assertNotIn("买 C-rebuy", text)
        self.assertIn("先核对银河旧买单", text)
        self.assertIn("若已成交", text)
        self.assertIn("旧单和资金核实后", text)
        self.assertIn("589720实时盘口", text)
        self.assertIn("不自动扩大单格", text)


if __name__ == "__main__":
    unittest.main()
