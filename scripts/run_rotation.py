"""Compatibility entry: invoke the single full-pool research CLI."""
import os
import sys

SYSTEM_PY = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
_IS_312 = sys.version_info[:2] == (3, 12) and 'Programs' in sys.executable

if __name__ == '__main__' and not _IS_312:
    import subprocess
    sys.stdout.flush(); sys.stderr.flush()
    sys.exit(subprocess.call([SYSTEM_PY, os.path.abspath(__file__)] + sys.argv[1:]))

import os
import sys
from pathlib import Path

REPO = Path(os.environ.get('ETF_RESEARCH_REPO', 'D:/Code/AH_analyse'))
sys.path.insert(0, str(REPO))
from tools.etf_research.research import main

if __name__ == '__main__':
    main()
