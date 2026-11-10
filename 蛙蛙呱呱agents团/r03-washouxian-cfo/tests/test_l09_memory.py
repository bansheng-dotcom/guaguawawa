# -*- coding: utf-8 -*-
import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.memory import FinancialSessionMemoryPool

class TestL09Memory(unittest.TestCase):
    def test_memory_snapshot_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "test_session_state.json")
            pool = FinancialSessionMemoryPool(storage_path=file_path)

            # 版本 1
            v1_id = pool.commit_snapshot("初版预算", {"runway": 12.0, "burn": 50000.0})
            # 版本 2
            v2_id = pool.commit_snapshot("修改版预算", {"runway": 8.0, "burn": 80000.0})

            self.assertEqual(pool.get_working_memory()["runway"], 8.0)

            # 执行回滚至 v1
            ok = pool.rollback(v1_id)
            self.assertTrue(ok)
            self.assertEqual(pool.get_working_memory()["runway"], 12.0)
            self.assertEqual(pool.get_working_memory()["burn"], 50000.0)

if __name__ == "__main__":
    unittest.main()
