"""00:01 scheduled sync for authoritative confirmed ETF subledgers only."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0, 'D:/Code/AH_analyse')
from grid_state import rollover

home = Path(__file__).resolve().parent.parent
for filename in ('confirmed-589720.json', 'confirmed-159363.json'):
    state = rollover(home/'cache/grid-account'/filename, datetime.now(timezone(timedelta(hours=8))).date().isoformat())
    print(f"{state['code']} 持有={state['qty']} 可卖={state['sellable_qty']} 最大序号={state['max_grid']} 更新日={state['sellable_updated_on']}")
