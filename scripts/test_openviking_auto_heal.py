# -*- coding: utf-8 -*-
"""TDD：OpenViking 守卫 2026-10-31 两次事故。

事故1（13:50）：服务器死 → 守卫 13 秒自愈成功，但 main() 返回 1，
  cron 把"自愈成功"标成 'Status: script failed' 推给用户（误报失败）。
  修复：重启成功 return 0（stdout 照常推送事件）。

事故2（15:05）：修事故1时新增"崩溃日志落盘"，写成
  OV_HOME / "logs" / "server-autoheal.log"，而 OV_HOME 是 **str**
  → TypeError: unsupported operand type(s) for /: 'str' and 'str'
  → 重启在落盘阶段就崩，服务器再也起不来（守卫自己成了故障点）。
  本测试锁死：start_server() 必须真正拉起子进程并返回 (True, 'launched')，
  且日志文件落在 OV_HOME/logs 下。
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / 'openviking_auto_heal.py'


def _load(tmp_home=None):
    """加载被测模块；tmp_home 给定时把 OV_HOME 等常量重定向到临时目录。"""
    spec = importlib.util.spec_from_file_location('ov_heal_under_test', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if tmp_home:
        mod.OV_HOME = str(tmp_home)
        mod.SERVER_EXE = os.path.join(str(tmp_home), 'venv', 'Scripts', 'openviking-server.exe')
    return mod


class StartServerTests(unittest.TestCase):
    """事故2：str / str 崩溃。"""

    def test_start_server_launches_and_returns_launched(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            exe = home / 'venv' / 'Scripts' / 'openviking-server.exe'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'')
            mod = _load(home)

            with mock.patch.object(mod.subprocess, 'Popen') as popen:
                popen.return_value = mock.Mock()
                ok, detail = mod.start_server()

            self.assertTrue(ok, f'start_server 应成功，实际 detail={detail}')
            self.assertEqual(detail, 'launched')
            popen.assert_called_once()
            log_file = home / 'logs' / 'server-autoheal.log'
            self.assertTrue(log_file.exists(), '崩溃日志文件必须被创建（事故2 落盘路径）')
            # 子进程参数：exe + host + port
            argv = popen.call_args[0][0]
            self.assertEqual(argv[0], str(exe))
            self.assertIn('--port', argv)

    def test_start_server_reports_missing_exe(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))  # venv 不存在
            ok, detail = mod.start_server()
            self.assertFalse(ok)
            self.assertIn('exe missing', detail)


class MainExitCodeTests(unittest.TestCase):
    """事故1：自愈成功必须是 exit 0，否则 cron 标 failed 推给用户。"""

    def _run_main(self, mod, health_seq):
        """health_seq 元素是 is_healthy() 的返回值 (healthy, detail)。"""
        seq = iter(health_seq)

        def fake_healthy():
            try:
                return next(seq)
            except StopIteration:
                return health_seq[-1]

        with mock.patch.object(mod, 'is_healthy', side_effect=fake_healthy), \
                mock.patch.object(mod, 'start_server', return_value=(True, 'launched')), \
                mock.patch.object(mod.time, 'sleep', return_value=None), \
                redirect_stdout(StringIO()) as buf:
            code = mod.main()
        return code, buf.getvalue()

    def test_healthy_is_silent_zero(self):
        mod = _load()
        code, out = self._run_main(mod, [(True, 'version=0.4.21')])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '', '健康时必须完全静默')

    def test_restart_success_returns_zero(self):
        mod = _load()
        code, out = self._run_main(mod, [(False, 'down'), (False, 'down'), (True, 'version=0.4.21')])
        self.assertEqual(code, 0, '自愈成功不能返回 1（cron 会误报 failed）')
        self.assertIn('restarted successfully', out)

    def test_restart_late_success_returns_zero(self):
        """超时窗口后才恢复——仍是自愈成功，不能报 failed。"""
        mod = _load()
        mod.START_TIMEOUT_S = 0  # 窗口立即耗尽 → 走"晚到恢复"分支
        with mock.patch.object(mod, 'is_healthy', side_effect=[(False, 'down'), (True, 'version=0.4.21')]), \
                mock.patch.object(mod, 'start_server', return_value=(True, 'launched')), \
                redirect_stdout(StringIO()) as buf:
            code = mod.main()
        self.assertEqual(code, 0, '晚到恢复仍属成功，返回 1 会被 cron 标 failed')
        self.assertIn('restarted', buf.getvalue())

    def test_restart_failure_returns_one(self):
        mod = _load()
        with mock.patch.object(mod, 'is_healthy', return_value=(False, 'down')), \
                mock.patch.object(mod, 'start_server', return_value=(False, 'launch failed: boom')), \
                redirect_stdout(StringIO()) as buf:
            code = mod.main()
        self.assertEqual(code, 1, '真失败必须非零，用户需要知道')
        self.assertIn('restart failed', buf.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
