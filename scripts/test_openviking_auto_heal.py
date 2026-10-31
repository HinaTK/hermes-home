# -*- coding: utf-8 -*-
"""TDD：OpenViking 守卫通知策略。

2026-10-31 用户明确要求：**成功不用告诉我，只有失败才汇报**。
（原话："看到汇报了，不过成功不用告诉我，只有失败的情况下才汇报"）

锁定四条行为：
1. 健康 → 完全静默（无输出、exit 0）。
2. 挂了但自愈成功 → 完全静默（本次需求核心）。
3. 自愈失败 / 服务器没回来 → 输出一条人话告警，且 exit 0
   （exit 0 是为了让 cron 直接把告警正文推给用户，而不是套上
   "Cron 'xxx' failed: Script exited with code 1 stdout: ..." 的机器外壳——
   那个外壳会把正文截断，用户读不了）。
4. 一小时内反复重启 ≥3 次 → 抖动告警（自愈"成功"但服务不稳，仍属失败），
   且一小时内只报一次，不刷屏。

历史事故（保留防回归）：
- 事故1（13:50）：自愈成功却 return 1 → cron 标 failed 误报。
- 事故2（15:05）：start_server 用 OV_HOME / "logs" 拼路径（OV_HOME 是 str）
  → TypeError，重启在落盘阶段就崩，守卫自己成了故障点。
"""
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / 'openviking_auto_heal.py'

T0 = 1_700_000_000.0  # 虚拟时钟起点，避免测试空转真实 45 秒


class FakeClock:
    """替换模块里的 time：sleep 推进虚拟时间，循环立刻耗尽/命中。"""

    def __init__(self, start=T0):
        self.t = start

    def time(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def _load(tmp_home=None):
    """加载被测模块；tmp_home 给定时把 OV_HOME / SERVER_EXE / STATE_FILE 重定向到临时目录。"""
    spec = importlib.util.spec_from_file_location('ov_heal_under_test', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if tmp_home:
        mod.OV_HOME = str(tmp_home)
        mod.SERVER_EXE = os.path.join(str(tmp_home), 'venv', 'Scripts', 'openviking-server.exe')
        mod.STATE_FILE = os.path.join(str(tmp_home), 'state', 'autoheal-state.json')
    return mod


def _seed_state(mod, restarts=(), last_flap_alert=None):
    os.makedirs(os.path.dirname(mod.STATE_FILE), exist_ok=True)
    state = {'restarts': list(restarts)}
    if last_flap_alert is not None:
        state['last_flap_alert'] = last_flap_alert
    with open(mod.STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f)


def run_main(mod, health_seq, start_result=(True, 'launched'), clock=None):
    """跑 mod.main()，is_healthy 按 health_seq 依次返回（耗尽后重复最后一项）。"""
    seq = iter(health_seq)

    def fake_healthy():
        try:
            return next(seq)
        except StopIteration:
            return health_seq[-1]

    clock = clock or FakeClock()
    with mock.patch.object(mod, 'is_healthy', side_effect=fake_healthy), \
            mock.patch.object(mod, 'start_server', return_value=start_result), \
            mock.patch.object(mod, 'time', clock), \
            redirect_stdout(StringIO()) as buf:
        code = mod.main()
    return code, buf.getvalue()


class StartServerTests(unittest.TestCase):
    """事故2：str / str 崩溃——start_server 必须真的能拉起进程。"""

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
            argv = popen.call_args[0][0]
            self.assertEqual(argv[0], str(exe))
            self.assertIn('--port', argv)

    def test_start_server_reports_missing_exe(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))  # venv 不存在
            ok, detail = mod.start_server()
            self.assertFalse(ok)
            self.assertIn('exe missing', detail)


class SilentOnSuccessTests(unittest.TestCase):
    """本次需求核心：成功路径不许出声。"""

    def test_healthy_is_silent_zero(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            code, out = run_main(mod, [(True, 'version=0.4.21')])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), '', '健康时必须完全静默')

    def test_restart_success_is_silent(self):
        """挂了→重启→恢复：用户不需要知道，不许推送。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            code, out = run_main(mod, [(False, 'down'), (True, 'version=0.4.21')])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), '', '自愈成功必须完全静默（用户 10-31 要求）')

    def test_restart_late_success_is_silent(self):
        """超时窗口后才恢复——仍是成功，也不许出声。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            code, out = run_main(mod, [(False, 'down'), (False, 'down'), (True, 'version=0.4.21')])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), '', '晚到恢复也算成功，不许出声')


class AlertOnFailureTests(unittest.TestCase):
    """失败必须出声，且必须是干净人话（不带 cron 机器外壳）。"""

    def test_restart_failure_prints_clean_alert(self):
        """重启命令执行失败 → 必须告警。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            code, out = run_main(mod, [(False, 'URLError: refused')],
                                 start_result=(False, 'launch failed: boom'))
            self.assertEqual(code, 0, 'exit 0 才能让正文原样推送（不带 Cron failed 外壳）')
            self.assertIn('OpenViking', out)
            self.assertIn('失败', out)
            self.assertIn('boom', out)

    def test_still_down_after_restart_prints_alert(self):
        """重启了但服务器没回来 → 必须告警。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            code, out = run_main(mod, [(False, 'URLError: refused')])
            self.assertEqual(code, 0)
            self.assertIn('OpenViking', out)
            self.assertIn('失败', out)
            self.assertIn('URLError', out, '告警要带上真实故障原因，不能只说"需要人工检查"')

    def test_alert_text_has_action_hint(self):
        """告警要能直接照着做。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            _code, out = run_main(mod, [(False, 'down')])
            self.assertIn('start-openviking.cmd', out, f'告警应给出可执行动作，实际：{out!r}')


class FlappingTests(unittest.TestCase):
    """反复重启=服务不稳定，属于"失败"，必须报；但不能每 5 分钟刷屏。"""

    def test_single_restart_does_not_alert(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            _seed_state(mod, restarts=[])
            _code, out = run_main(mod, [(False, 'down'), (True, 'version=0.4.21')])
            self.assertEqual(out.strip(), '', '单次自愈成功不许出声')

    def test_flapping_alerts_even_though_heal_succeeded(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            clock = FakeClock()
            # 一小时内已经重启过 2 次，本次是第 3 次 → 触发抖动告警
            _seed_state(mod, restarts=[clock.t - 600, clock.t - 300])
            code, out = run_main(mod, [(False, 'down'), (True, 'version=0.4.21')], clock=clock)
            self.assertEqual(code, 0)
            self.assertIn('3', out, f'告警应给出次数，实际：{out!r}')
            self.assertIn('重启', out)

    def test_flap_alert_deduped_within_window(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            clock = FakeClock()
            _seed_state(mod, restarts=[clock.t - 600, clock.t - 300, clock.t - 120],
                        last_flap_alert=clock.t - 60)
            _code, out = run_main(mod, [(False, 'down'), (True, 'version=0.4.21')], clock=clock)
            self.assertEqual(out.strip(), '', '抖动告警一小时内只报一次，不刷屏')

    def test_restart_history_recorded_after_heal(self):
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            _seed_state(mod, restarts=[])
            run_main(mod, [(False, 'down'), (True, 'version=0.4.21')])
            with open(mod.STATE_FILE, encoding='utf-8') as f:
                state = json.load(f)
            self.assertEqual(len(state.get('restarts', [])), 1,
                             '每次重启都要落盘，否则抖动判定失效')

    def test_healthy_clears_restart_history(self):
        """恢复正常后清空历史，避免隔天把旧重启算成抖动。"""
        with tempfile.TemporaryDirectory() as td:
            mod = _load(Path(td))
            clock = FakeClock()
            _seed_state(mod, restarts=[clock.t - 600, clock.t - 300])
            run_main(mod, [(True, 'version=0.4.21')], clock=clock)
            with open(mod.STATE_FILE, encoding='utf-8') as f:
                state = json.load(f)
            self.assertEqual(state.get('restarts'), [], '健康时清空重启历史')


if __name__ == '__main__':
    unittest.main(verbosity=2)
