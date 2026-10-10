# -*- coding: utf-8 -*-
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path
import tempfile

import grid_account as g

TZ = ZoneInfo("Asia/Shanghai")


def _book():
    tmp = Path(tempfile.mkdtemp())
    g.ROOT = tmp
    g.LEDGER = tmp / "ledger.json"
    g.TICKETS = tmp / "tickets"
    return g.seed()


def test_phase_clock():
    pre = datetime(2026, 9, 24, 9, 10, tzinfo=TZ)
    open_ = datetime(2026, 9, 24, 9, 31, tzinfo=TZ)
    sat = datetime(2026, 9, 26, 9, 32, tzinfo=TZ)
    mid_autumn = datetime(2026, 9, 25, 9, 32, tzinfo=TZ)
    assert g.session_phase(pre) == "preview"
    assert g.session_phase(open_) == "execute"
    assert g.session_phase(sat) == "closed"
    assert g.session_phase(mid_autumn) == "closed"
    assert g.next_session(date(2026, 9, 24)) == date(2026, 9, 28)
    assert g.EXECUTE_HHMM == 931


def test_preview_does_not_lock_limit():
    book = _book()
    quotes = {
        "sz159992": {"last": "0.867", "prev": "0.867"},
        "sz159363": {"last": "1.291", "prev": "1.291"},
    }
    d = date(2026, 9, 28)
    preview = g.plan(book, quotes, d, phase="preview", live=False)
    assert preview["status"] == "preview"
    assert preview["actions"] == []
    assert "禁止按此价成交" in preview["note"]
    text = g.render(book, preview)
    assert "勿下单" in text
    assert "9:31" in text
    try:
        g.apply(book, "成功", d)
        raise AssertionError("preview apply should fail")
    except ValueError as e:
        assert "预告" in str(e)

    live = {
        "sz159992": {"last": "0.875", "prev": "0.867"},
        "sz159363": {"last": "1.270", "prev": "1.291"},
    }
    exe = g.plan(book, live, d, phase="execute", live=True)
    assert exe["phase"] == "execute"
    assert exe["status"] == "none"
    assert exe["actions"] == []
    text2 = g.render(book, exe)
    assert "无新增操作" in text2


if __name__ == "__main__":
    test_phase_clock()
    test_preview_does_not_lock_limit()
    print("ok")
