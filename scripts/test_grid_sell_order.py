# -*- coding: utf-8 -*-
"""Lowest eligible lot goes first; T+1 and stale-ticket handling."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import grid_account as g


class SellOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tickets = Path(self.tmp.name) / "tickets"
        self.tickets.mkdir()
        self.target = patch.object(g, "TICKETS", self.tickets)
        self.target.start()
        self.addCleanup(self.target.stop)
        self.ledger_target = patch.object(g, "LEDGER", Path(self.tmp.name) / "ledger.json")
        self.ledger_target.start()
        self.addCleanup(self.ledger_target.stop)
        self.day = date(2026, 9, 28)
        self.quotes = {
            "sz159992": {"last": "0.839", "prev": "0.841"},
            "sz159363": {"last": "1.170", "prev": "1.246"},
        }
        self.book = {
            "cash": 58535.2,
            "history": [{"date": self.day.isoformat(), "result": "成功", "actions": [
                {"side": "buy", "code": "sz159363", "qty": 4800, "lot": "C", "price": 1.197}
            ]}],
            "positions": {
                "sz159992": {"qty": 27700, "second_pending": 0, "rebuy": [], "lots": [
                    {"id": "A", "qty": 9100, "price": 0.871, "sell": 0.888, "available_from": "2026-09-24"},
                    {"id": "B", "qty": 9200, "price": 0.863, "sell": 0.880, "available_from": "2026-09-28"},
                    {"id": "C", "qty": 9400, "price": 0.846, "sell": 0.863, "available_from": "2026-09-28"},
                ]},
                "sz159363": {"qty": 14100, "second_pending": 0, "rebuy": [], "lots": [
                    {"id": "A", "qty": 4600, "price": 1.280, "sell": 1.306, "available_from": "2026-09-24"},
                    {"id": "B", "qty": 4700, "price": 1.273, "sell": 1.298, "available_from": "2026-09-28"},
                    {"id": "C", "qty": 4800, "price": 1.197, "sell": 1.221, "available_from": "2026-09-29"},
                ]},
            },
        }

    def test_sell_lowest_eligible_and_dynamic_adds_for_deep_drop(self):
        ticket = g.plan(self.book, self.quotes, self.day)
        sells = {a["code"]: a for a in ticket["actions"] if a["side"] == "sell"}
        self.assertEqual((sells["sz159992"]["lot"], sells["sz159992"]["qty"], sells["sz159992"]["price"]), ("C", 9400, 0.863))
        self.assertEqual((sells["sz159363"]["lot"], sells["sz159363"]["qty"], sells["sz159363"]["price"]), ("C", 4800, 1.221))
        preview = g.render(self.book, {**ticket, "phase": "preview", "actions": []})
        self.assertIn("卖价=0.863", preview)
        self.assertIn("卖价=1.221", preview)

    def test_preview_accepts_date_object_without_crashing(self):
        ticket = g.plan(self.book, self.quotes, self.day, phase="preview", live=False)
        self.assertEqual(ticket["status"], "preview")
        self.assertIn("勿下单", g.render(self.book, ticket))

    def test_preview_does_not_reprint_pending_execute_ticket(self):
        active = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863, "lot": "C"}
        ], "quotes": self.quotes}
        path = self.tickets / "2026-09-28.json"
        path.write_text(json.dumps(active), encoding="utf-8")
        preview = g.plan(self.book, self.quotes, self.day, phase="preview", live=False)
        self.assertEqual(preview["phase"], "preview")
        self.assertEqual(preview["actions"], [])
        self.assertIn("勿下单", g.render(self.book, preview))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), active)

    def test_executable_ticket_uses_two_line_per_etf_layout(self):
        ticket = {"date": self.day.isoformat(), "phase": "execute", "live": True,
            "quotes": self.quotes, "actions": [
                {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863},
                {"side": "buy", "code": "sz159992", "qty": 9600, "price": 0.829},
                {"side": "sell", "code": "sz159363", "qty": 5100, "price": 1.192},
                {"side": "buy", "code": "sz159363", "qty": 5200, "price": 1.146},
            ]}
        text = g.render(self.book, ticket)
        self.assertIn("**159992 创新药ETF银华**\n- 卖：**9,400 份 @ 0.863**\n- 买：**9,600 份 @ 0.829**", text)
        self.assertIn("**159363 创业板人工智能ETF华宝**\n- 卖：**5,100 份 @ 1.192**\n- 买：**5,200 份 @ 1.146**", text)
        self.assertNotIn("回：成功 或 失败", text)

    def test_executable_ticket_uses_grid_letter_and_bold_amounts(self):
        ticket = {"date": self.day.isoformat(), "phase": "execute", "live": True,
            "quotes": self.quotes, "actions": [
                {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863, "lot": "C"},
                {"side": "buy", "code": "sz159992", "qty": 9600, "price": 0.829, "lot": "D"},
                {"side": "sell", "code": "sz159363", "qty": 4700, "price": 1.298, "lot": "B"},
                {"side": "buy", "code": "sz159363", "qty": 5200, "price": 1.146, "lot": "E"},
            ]}
        text = g.render(self.book, ticket)
        self.assertIn("**现在的剩余操作建议**", text)
        self.assertIn("**159992 创新药ETF银华**\n- 卖 C 格：**9,400 份 @ 0.863**\n- 买 D 格：**9,600 份 @ 0.829**", text)
        self.assertIn("**159363 创业板人工智能ETF华宝**\n- 卖 B 格：**4,700 份 @ 1.298**\n- 买 E 格：**5,200 份 @ 1.146**", text)

    def test_stale_high_sell_is_replaced(self):
        stale = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9100, "price": 0.888, "lot": "A"}
        ]}
        (self.tickets / "2026-09-28.json").write_text(json.dumps(stale), encoding="utf-8")
        ticket = g.plan(self.book, self.quotes, self.day)
        self.assertEqual(next(a for a in ticket["actions"] if a["side"] == "sell" and a["code"] == "sz159992")["lot"], "C")
        self.assertTrue((self.tickets / "2026-09-28-1.json").exists())

    def test_confirmed_c_sell_keeps_rebuy_and_staged_d_buy(self):
        self.day = date(2026, 9, 29)
        pos = self.book["positions"]["sz159992"]
        pos["lots"][2]["qty"] = 0
        pos["qty"] = 18300
        pos["rebuy"] = [{"qty": 9400, "price": .846, "from_lot": "C"}]
        other = self.book["positions"]["sz159363"]
        other["lots"].append({"id": "D", "qty": 5100, "price": 1.169, "sell": 1.192, "available_from": "2026-09-29"})
        other["qty"] += 5100
        ticket = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9200, "price": .880, "lot": "B"},
            {"side": "buy", "code": "sz159992", "qty": 9400, "price": .846, "lot": "C-rebuy", "rebuy": True},
            {"side": "buy", "code": "sz159992", "qty": 9600, "price": .829, "lot": "D", "down_grid": True},
            {"side": "sell", "code": "sz159363", "qty": 5100, "price": 1.192, "lot": "D"},
            {"side": "buy", "code": "sz159363", "qty": 5200, "price": 1.146, "lot": "E", "down_grid": True},
        ]}
        path = self.tickets / "2026-09-29.json"
        path.write_text(json.dumps(ticket), encoding="utf-8")
        result = g.plan(self.book, self.quotes, self.day)
        self.assertEqual(result["actions"], ticket["actions"])
        self.assertFalse((self.tickets / "2026-09-29-1.json").exists())

    def test_rebought_c_becomes_nearest_sell_and_keeps_d_buy(self):
        self.day = date(2026, 9, 29)
        pos = self.book["positions"]["sz159992"]
        pos["lots"][2]["qty"] = 0
        pos["lots"].append({"id": "C-rebuy", "qty": 9400, "price": .846,
                             "sell": .863, "available_from": "2026-09-30"})
        pos["rebuy"] = []
        other = self.book["positions"]["sz159363"]
        other["lots"].append({"id": "D", "qty": 5100, "price": 1.169,
                              "sell": 1.192, "available_from": "2026-09-29"})
        old = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "actions": [
            {"side": "buy", "code": "sz159992", "qty": 9600, "price": .829, "lot": "D", "down_grid": True},
            {"side": "sell", "code": "sz159992", "qty": 9200, "price": .880, "lot": "B"},
            {"side": "buy", "code": "sz159992", "qty": 9400, "price": .846, "lot": "C-rebuy", "rebuy": True},
        ]}
        (self.tickets / "2026-09-29.json").write_text(json.dumps(old), encoding="utf-8")
        result = g.plan(self.book, self.quotes, self.day)
        actions = [a for a in result["actions"] if a["code"] == "sz159992"]
        self.assertEqual([(a["side"], a["lot"], a["qty"], a["price"]) for a in actions],
                         [("sell", "C-rebuy", 9400, .863), ("buy", "D", 9600, .829)])
        self.assertTrue((self.tickets / "2026-09-29-1.json").exists())

    def test_protected_core_is_not_sold_on_one_way_rise(self):
        pos = self.book["positions"]["sz159992"]
        pos["lots"][1]["qty"] = pos["lots"][2]["qty"] = 0
        pos["qty"] = 9100
        self.quotes["sz159992"]["last"] = "1.000"
        ticket = g.plan(self.book, self.quotes, self.day)
        self.assertFalse(any(a["side"] == "sell" and a["code"] == "sz159992" for a in ticket["actions"]))
        preview = g.plan(self.book, self.quotes, self.day, phase="preview", live=False)
        self.assertIn("参与底仓保留不卖", g.render(self.book, preview))
        self.assertEqual(pos["qty"], 9100)

    def test_pending_core_sell_is_invalidated_not_preserved(self):
        pos = self.book["positions"]["sz159992"]
        pos["lots"][1]["qty"] = pos["lots"][2]["qty"] = 0
        pos["qty"] = 9100
        old = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9100, "price": .888, "lot": "A"}]}
        (self.tickets / "2026-09-28.json").write_text(json.dumps(old), encoding="utf-8")
        result = g.plan(self.book, self.quotes, self.day)
        self.assertFalse(any(a["side"] == "sell" and a["code"] == "sz159992" for a in result["actions"]))
        self.assertTrue((self.tickets / "2026-09-28-1.json").exists())

    def test_confirmed_legacy_sell_is_recorded_even_if_it_breaches_core(self):
        pos = self.book["positions"]["sz159992"]
        pos["lots"][1]["qty"] = pos["lots"][2]["qty"] = 0
        pos["qty"] = 9100
        pos["lots"][0]["bought"] = "2026-09-23"
        pos["cost_cash"] = 9100 * pos["lots"][0]["price"] + 5
        ticket = {"date": self.day.isoformat(), "phase": "execute", "status": "pending", "quotes": self.quotes, "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9100, "price": .888, "lot": "A"}]}
        (self.tickets / "2026-09-28.json").write_text(json.dumps(ticket), encoding="utf-8")
        recorded, ticket = g.apply(self.book, "成功", self.day)
        self.assertEqual(recorded["positions"]["sz159992"]["qty"], 0)
        self.assertTrue(ticket["core_breached"])
        self.assertIn("底仓已被实际成交耗尽", g.render(recorded, ticket))

    def test_sold_d_rebuy_preserves_c_sell_and_e_buy(self):
        self.day = date(2026, 9, 30)
        pos = self.book["positions"]["sz159363"]
        pos["qty"] = 14100
        pos["lots"].append({"id": "D", "qty": 0, "price": 1.169,
                            "sell": 1.192, "available_from": "2026-09-29"})
        pos["rebuy"] = [{"qty": 5100, "price": 1.169, "from_lot": "D"}]
        self.book["cash"] = 58792.3
        first = g.plan(self.book, self.quotes, self.day)
        acts = [(a["side"], a.get("lot"), a["qty"], a["price"])
                for a in first["actions"] if a["code"] == "sz159363"]
        self.assertEqual(acts, [("buy", "D-rebuy", 5100, 1.169),
                                ("sell", "C", 4800, 1.221),
                                ("buy", "E", 5200, 1.146)])
        again = g.plan(self.book, self.quotes, self.day)
        self.assertEqual(again["actions"], first["actions"])
        self.assertFalse((self.tickets / "2026-09-30-1.json").exists())

    def test_next_day_c_is_eligible_for_363(self):
        self.assertEqual(g.next_sell_lot(self.book["positions"]["sz159363"], date(2026, 9, 29))["id"], "C")


if __name__ == "__main__":
    unittest.main()
