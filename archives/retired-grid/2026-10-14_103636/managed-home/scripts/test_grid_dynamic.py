# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import grid_account as g
import grid_weixin_intraday as intraday


class DynamicGridTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tickets = Path(self.tmp.name) / "tickets"
        self.tickets.mkdir()
        self.target = patch.object(g, "TICKETS", self.tickets)
        self.target.start()
        self.addCleanup(self.target.stop)
        intraday_target = patch.object(intraday, "TICKETS", self.tickets)
        intraday_target.start()
        self.addCleanup(intraday_target.stop)
        self.day = date(2026, 9, 28)
        self.book = {
            "cash": 58535.2,
            "history": [],
            "positions": {
                "sz159992": {"qty": 27700, "second_pending": 0, "rebuy": [], "lots": [
                    {"id": "A", "qty": 9100, "price": 0.871, "sell": 0.888, "available_from": "2026-09-24"},
                    {"id": "B", "qty": 9200, "price": 0.863, "sell": 0.880, "available_from": "2026-09-28"},
                    {"id": "C", "qty": 9400, "price": 0.846, "sell": 0.863, "available_from": "2026-09-28"},
                ]},
                "sz159363": {"qty": 14100, "second_pending": 0, "rebuy": [], "lots": [
                    {"id": "A", "qty": 4600, "price": 1.280, "sell": 1.306, "available_from": "2026-09-24"},
                ]},
            },
        }

    def test_price_crossing_multiple_levels_creates_multiple_buys(self):
        quotes = {
            "sz159992": {"last": "0.790", "prev": "0.841"},
            "sz159363": {"last": "1.280", "prev": "1.280"},
        }
        ticket = g.plan(self.book, quotes, self.day)
        buys = [a for a in ticket["actions"] if a["code"] == "sz159992" and a["side"] == "buy"]
        self.assertGreaterEqual(len(buys), 2)
        self.assertEqual([a["price"] for a in buys], sorted([a["price"] for a in buys], reverse=True))
        self.assertTrue(all(a["price"] >= 0.790 for a in buys))

    def test_intraday_crossing_alerts_down_and_up_once(self):
        ticket = {"status": "pending", "actions": [
            {"side": "buy", "code": "sz159992", "qty": 9600, "price": 0.829, "lot": "D"},
            {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863, "lot": "C"},
        ]}
        state = {"prices": {}, "alerts": {}}
        self.assertIsNone(intraday.trend_alert(ticket, {"sz159992": {"last": "0.850"}}, state))
        down = intraday.trend_alert(ticket, {"sz159992": {"last": "0.820"}}, state)
        self.assertIn("下探1格", down)
        state["prices"]["sz159992"] = 0.820
        up = intraday.trend_alert(ticket, {"sz159992": {"last": "0.870"}}, state)
        self.assertIn("上探1格", up)

    def test_first_spot_touch_without_day_extrema_alerts_once(self):
        ticket = {"status": "pending", "actions": [
            {"side": "buy", "code": "sz159992", "qty": 9400, "price": 0.846},
            {"side": "buy", "code": "sz159992", "qty": 9600, "price": 0.829},
        ]}
        state = {"prices": {}, "alerts": {}}
        quote = {"sz159992": {"last": "0.840"}}
        msg = intraday.trend_alert(ticket, quote, state)
        self.assertIsNotNone(msg)
        self.assertIn("现价0.840", msg)
        self.assertNotIn("今日最低", msg)
        self.assertIsNone(intraday.trend_alert(ticket, quote, state))
        msg = intraday.trend_alert(ticket, {"sz159992": {"last": "0.820"}}, state)
        self.assertIn("0.829（9600份）", msg)
        self.assertNotIn("0.846（9400份）", msg)

    def test_original_day_low_alert_accepts_pre_ticket_touch_once(self):
        ticket = {"status": "pending", "actions": [
            {"side": "buy", "code": "sz159992", "qty": 9400, "price": 0.846, "lot": "C-rebuy"},
        ]}
        state = {"prices": {}, "alerts": {}}
        quote = {"sz159992": {"last": "0.862", "high": "0.864", "low": "0.839"}}
        msg = intraday.trend_alert(ticket, quote, state)
        self.assertIsNotNone(msg)
        self.assertIn("今日最低0.839", msg)
        self.assertIn("可能发生在建议挂单之前", msg)
        self.assertIsNone(intraday.trend_alert(ticket, quote, state))

    def test_new_ticket_keeps_day_extrema_without_baseline_cutoff(self):
        old = {"status": "pending", "actions": [{"side": "buy", "code": "sz159992", "qty": 9600, "price": 0.829}]}
        new = {"status": "pending", "actions": [{"side": "buy", "code": "sz159992", "qty": 9400, "price": 0.846}]}
        state = {"prices": {}, "alerts": {}}
        self.assertIsNone(intraday.trend_alert(old, {"sz159992": {"last": "0.862", "low": "0.850"}}, state))
        self.assertIn("今日最低0.839", intraday.trend_alert(new, {"sz159992": {"last": "0.862", "low": "0.839"}}, state))

    def test_existing_minute_state_preserves_one_shot_dedup(self):
        ticket = {"status": "pending", "actions": [
            {"side": "buy", "code": "sz159992", "qty": 9400, "price": 0.846},
        ], "issued_at": "2026-09-30T10:59:00+08:00"}
        ticket["issued_actions"] = intraday.fp(ticket)
        state = {"monitor_version": "minute-bars-v1", "action_fp": "old-fingerprint",
                 "alerts": {"sz159992:down:0.846": True}, "prices": {}}
        self.assertIsNone(intraday.trend_alert(ticket, {"sz159992": {"last": "0.862", "low": "0.839"}}, state))
        state["alerts"].clear()
        self.assertIn("今日最低0.839", intraday.trend_alert(ticket, {"sz159992": {"last": "0.862", "low": "0.839"}}, state))

    def test_high_touched_between_snapshots_alerts_once_without_claiming_fill(self):
        ticket = {"status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863, "lot": "C"},
        ]}
        state = {"prices": {}, "alerts": {}}
        quotes = {"sz159992": {"last": "0.858", "high": "0.863", "low": "0.838"}}
        msg = intraday.trend_alert(ticket, quotes, state)
        self.assertIn("今日最高0.863", msg)
        self.assertIn("请核对银河委托/成交", msg)
        self.assertIsNone(intraday.trend_alert(ticket, quotes, state))

    def test_fresh_high_only_alerts_new_levels(self):
        ticket = {"status": "pending", "actions": [
            {"side": "sell", "code": "sz159992", "qty": 9400, "price": 0.863},
            {"side": "sell", "code": "sz159992", "qty": 9200, "price": 0.880},
        ]}
        state = {"prices": {}, "alerts": {}}
        self.assertIn("0.863", intraday.trend_alert(ticket, {"sz159992": {"last": "0.850", "high": "0.863"}}, state))
        msg = intraday.trend_alert(ticket, {"sz159992": {"last": "0.870", "high": "0.880"}}, state)
        self.assertIn("0.880", msg)
        self.assertNotIn("0.863", msg)


class OriginalIntradayMainTests(unittest.TestCase):
    def test_main_uses_day_extrema_without_minute_request_or_real_book_writes(self):
        import io
        from contextlib import redirect_stdout
        from datetime import datetime

        with tempfile.TemporaryDirectory() as tmp:
            tickets = Path(tmp) / "tickets"
            tickets.mkdir()
            day = date(2026, 9, 30)
            ticket = {"status": "pending", "actions": [
                {"side": "buy", "code": "sz159992", "qty": 9400, "price": 0.846},
            ]}
            path = tickets / f"{day.isoformat()}.json"
            path.write_text(json.dumps(ticket), encoding="utf-8")
            quotes = {"sz159992": {"last": "0.862", "low": "0.839", "high": "0.864"}}
            with patch.object(intraday, "TICKETS", tickets), \
                 patch.object(intraday, "datetime") as clock, \
                 patch.object(intraday, "today", return_value=day), \
                 patch.object(intraday, "session_phase", return_value="execute"), \
                 patch.object(intraday, "fetch_quotes", return_value=quotes), \
                 patch.object(intraday, "quotes_are_live", return_value=True), \
                 patch.object(intraday, "fetch_minute_bars", create=True, side_effect=AssertionError("minute feed must be disabled")) as minutes, \
                 patch.object(intraday, "load", side_effect=AssertionError("must not load ledger")), \
                 patch.object(intraday, "plan", side_effect=AssertionError("must not replan pending ticket")):
                clock.now.return_value = datetime(2026, 9, 30, 10, 40, tzinfo=intraday.TZ)
                first = io.StringIO()
                with redirect_stdout(first):
                    intraday.main()
                self.assertIn("今日最低0.839", first.getvalue())
                second = io.StringIO()
                with redirect_stdout(second):
                    intraday.main()
                self.assertEqual(second.getvalue(), "")
                quotes["sz159992"]["last"] = "0.840"
                third = io.StringIO()
                with redirect_stdout(third):
                    intraday.main()
                self.assertEqual(third.getvalue(), "")
                minutes.assert_not_called()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), ticket)
            state = json.loads((tickets.parent / "intraday_trend_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["alerts"]["sz159992:down:0.846"])


if __name__ == "__main__":
    unittest.main()
