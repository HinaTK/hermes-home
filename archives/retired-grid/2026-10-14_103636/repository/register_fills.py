"""Register two explicit confirmed fills with today's date and sequential IDs."""
import json
import shutil
from pathlib import Path

from grid_state import record

HOME = Path('D:/Hermes Agent CN Desktop/data/hermes-home/cache/grid-account')
DAY = '2026-10-14'

FILLS = [
    ('sh589720', 'buy', 9800, '0.807', '589720-010'),
    ('sz159363', 'buy', 5400, '1.097', '159363-017'),
]

for code, side, qty, price, eid in FILLS:
    path = HOME / f'confirmed-{code[-6:]}.json'
    before = path.read_bytes()
    state = record(path, side, qty, price, DAY, execution_id=eid)
    after = path.read_bytes()
    print(f"{code} {side} {qty} @{price} id={eid} "
          f"qty={state['qty']} sellable={state['sellable_qty']} "
          f"max_grid={state['max_grid']} net={state['net_invested']} "
          f"t_net={state['t_net']} changed={before != after}")