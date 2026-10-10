# -*- coding: utf-8 -*-
"""Weekday 09:10 WeChat preview. Do not treat as a fillable order."""
import sys
from pathlib import Path

sys.argv = [sys.argv[0], "--phase", "preview"]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_weixin_ops  # noqa: E402

if __name__ == "__main__":
    grid_weixin_ops.main()
