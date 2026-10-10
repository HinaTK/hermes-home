# -*- coding: utf-8 -*-
"""Weekday 09:31 Feishu ticket, executable only after a fresh quote."""
import sys
from pathlib import Path

sys.argv = [sys.argv[0], "--phase", "execute"]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_weixin_ops  # noqa: E402

if __name__ == "__main__":
    grid_weixin_ops.main()
