import unittest
import importlib.util
from pathlib import Path

class GuardTests(unittest.TestCase):
    def test_missing_reconciled_etf_blocks_legacy_plan(self):
        path=Path('D:/Hermes Agent CN Desktop/data/hermes-home/scripts/grid_runtime_guard.py')
        self.assertTrue(path.exists(), 'missing safety guard')
        spec=importlib.util.spec_from_file_location('guard',path)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertIn('勿下单',mod.block_reason({'positions':{'sz159363':{}}}))
        self.assertIn('勿下单',mod.block_reason({'positions':{'sz159363':{},'sh589720':{}}}))

if __name__=='__main__': unittest.main()
