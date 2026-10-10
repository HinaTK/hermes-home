# -*- coding: utf-8 -*-
"""Migration regressions; every ledger, ticket and policy path is temporary."""
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

import grid_account as g


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tickets = self.root / "tickets"
        self.tickets.mkdir()
        for name, value in (("ROOT", self.root), ("LEDGER", self.root / "ledger.json"), ("TICKETS", self.tickets)):
            mock = patch.object(g, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.day = date(2026, 9, 30)
        self.policy = {"enabled": True, "source": "sz159992", "target": "sh589720",
                       "stage": "awaiting_broker_reconciliation", "group_cost_cap": 46000,
                       "release_source_core": True, "target_buy_enabled": False}
        (self.root / "migration.json").write_text(json.dumps(self.policy), encoding="utf-8")
        self.book = {"cash": 66899.5, "history": [], "positions": {
            "sz159992": {"qty": 18300, "cost_cash": 15875.7, "second_pending": 0,
                         "lots": [{"id": "A", "qty": 9100, "price": .871, "sell": .888,
                                   "bought": "2026-09-23", "available_from": "2026-09-24"},
                                  {"id": "B", "qty": 9200, "price": .863, "sell": .880,
                                   "bought": "2026-09-24", "available_from": "2026-09-28"}],
                         "rebuy": [{"qty": 9400, "price": .846, "from_lot": "C-rebuy"}]},
            "sz159363": {"qty": 4600, "cost_cash": 5893, "second_pending": 0,
                         "lots": [{"id": "A", "qty": 4600, "price": 1.28, "sell": 1.306,
                                   "bought": "2026-09-23", "available_from": "2026-09-24"}], "rebuy": []}}}
        self.quotes = {"sz159992": {"last": ".846", "prev": ".844"},
                       "sz159363": {"last": "1.194", "prev": "1.183"}}

    def test_pending_source_buys_are_removed_from_local_suggestions_not_claimed_cancelled(self):
        old = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "live": True,
               "quotes": self.quotes, "actions": [
                   {"code": "sz159992", "side": "buy", "qty": 9400, "price": .846, "lot": "C-rebuy", "rebuy": True},
                   {"code": "sz159992", "side": "buy", "qty": 9600, "price": .829, "lot": "D", "down_grid": True},
                   {"code": "sz159992", "side": "sell", "qty": 9200, "price": .880, "lot": "B"},
                   {"code": "sz159363", "side": "buy", "qty": 5100, "price": 1.169, "lot": "D-rebuy", "rebuy": True}]}
        (self.tickets / f"{self.day}.json").write_text(json.dumps(old), encoding="utf-8")
        before = deepcopy(self.book)
        ticket = g.plan(self.book, self.quotes, self.day)
        self.assertFalse(any(a["code"] == "sz159992" and a["side"] == "buy" for a in ticket["actions"]))
        self.assertEqual(len(ticket["withdrawal_actions"]), 2)
        self.assertFalse(ticket["migration"]["broker_cancel_confirmed"])
        self.assertEqual(self.book, before)
        self.assertFalse(any(a["code"] == "sh589720" for a in ticket["actions"]))
    def test_fresh_exit_ticket_does_not_invent_more_source_buy_orders_to_cancel(self):
        ticket = g.plan(self.book, self.quotes, self.day)
        self.assertFalse(any(a["code"] == "sz159992" and a["side"] == "buy" for a in ticket["actions"]))
        self.assertEqual(ticket["withdrawal_actions"], [])
        self.assertIn("迁移退出", ticket["note"])
    def test_migration_can_exit_last_core_lot_without_changing_other_etf_core(self):
        pos = deepcopy(self.book["positions"]["sz159992"])
        pos["lots"] = pos["lots"][:1]
        pos["qty"] = 9100
        lot = g.next_sell_lot(pos, self.day, "sz159992")
        self.assertIsNotNone(lot)
        self.assertEqual(lot["id"], "A")
        self.assertIsNone(g.next_sell_lot(self.book["positions"]["sz159363"], self.day, "sz159363"))
    def test_source_sale_retires_named_lot_without_creating_new_rebuy(self):
        ticket = {"date": str(self.day), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9200, "price": .88, "lot": "B"}]}
        (self.tickets / f"{self.day}.json").write_text(json.dumps(ticket), encoding="utf-8")
        old_rebuys = deepcopy(self.book["positions"]["sz159992"]["rebuy"])
        book, _ = g.apply(self.book, "成功", self.day)
        pos = book["positions"]["sz159992"]
        self.assertEqual(pos["rebuy"], old_rebuys)
        self.assertEqual({lot["id"]: lot["qty"] for lot in pos["lots"]}, {"A": 9100, "B": 0})

    def test_intraday_does_not_remind_source_buy_after_migration_authorized(self):
        import grid_weixin_intraday as intraday
        ticket = {"actions": [{"code": "sz159992", "side": "buy", "qty": 9400, "price": .846}]}
        with patch.object(intraday, "TICKETS", self.tickets):
            self.assertIsNone(intraday.trend_alert(ticket, {"sz159992": {"last": ".84", "low": ".839"}}, {"alerts": {}}))

    def test_render_discloses_broker_cancellation_pending(self):
        ticket = g.plan(self.book, self.quotes, self.day)
        text = g.render(self.book, ticket)
        self.assertIn("本地停买不代表已撤单", text)
        self.assertIn("589720", text)
    def test_after_close_review_cannot_rebase_retiring_etf(self):
        import grid_eod_decision as eod
        report = {"for_session": str(self.day), "decisions": {"sz159992": {
            "state": "REVIEW_REBASE", "watch_price": .90, "reason": "old uptrend"}}}
        note = eod.next_day_note(report, self.day, "preview")
        self.assertIn("迁移退出", note)
        self.assertNotIn("低库存上移候选", note)
        self.assertNotIn("观察回踩价", note)
        bars = [{"date": str(self.day), "close": .872} for _ in range(25)]
        self.assertEqual(eod.assess("sz159992", self.book, bars, self.day)["state"], "MIGRATION_EXIT")
    def test_migration_rejects_ambiguous_bulk_fill_confirmation(self):
        ticket = {"date": str(self.day), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9200, "price": .88, "lot": "B"},
            {"side": "sell", "code": "sz159363", "qty": 4600, "price": 1.306, "lot": "A"}]}
        (self.tickets / f"{self.day}.json").write_text(json.dumps(ticket), encoding="utf-8")
        before = deepcopy(self.book)
        with self.assertRaisesRegex(ValueError, "逐笔"):
            g.apply(self.book, "成功", self.day)
        self.assertEqual(self.book, before)
    def test_render_does_not_reprint_legacy_source_buy_as_an_order(self):
        ticket = {"date": str(self.day), "phase": "execute", "actions": [
            {"code": "sz159992", "side": "buy", "qty": 9400, "price": .846, "lot": "C"}]}
        self.assertNotIn("- 买 C 格", g.render(self.book, ticket))


if __name__ == "__main__":
    unittest.main()
