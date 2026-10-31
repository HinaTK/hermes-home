# -*- coding: utf-8 -*-
"""TDD：网关守护两代事故（2026-10-31 同日两次）。

事故1（04:09-10:04，误报×70）：
- 网关被外部杀掉后由 .bat 拉起，新实例 pid=109352 把 PID 文件写到 hermes-home/；
- keeper 只读旧位置 gateway-runtime/（死 pid=10900，10-26 残留）→ 误判"未运行"；
- 且 PID 文件存在但 PID 已死时直接判死，走不到进程名兜底 → 连续 70 次报警。
修复1：PID 文件覆盖新旧两位置（任一活=活）；全死走进程名兜底。

事故2（10:30-10:56，漏报27分钟）：
- 网关 109352 死了，桌面 App 同时重启，其后端 dashboard 进程（101920）与网关
  **同一个 exe 名**（hermes-agent-cn-runtime-win32-x64.exe，argv=dashboard --host...）；
- 修复1引入的进程名兜底把 dashboard 误认成网关 → keeper 连续4轮静默，飞书断27分钟。
修复2：一切进程名兜底/PID验活必须做**命令行身份核验**（CommandLine 含 gateway
才算网关）；wmic 不可用时才退回信任 PID 文件。

测试通过 monkeypatch _tasklist / _wmic_processes 隔离本机真实进程。
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / 'gateway_keeper.py'


def _load():
    spec = importlib.util.spec_from_file_location('gk_under_test', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk_tasklist(pid_map, image_line=None):
    """pid_map: {pid: 是否存活}；image_line: IMAGENAME 查询返回的进程行（None=查无）。"""
    class _R:  # 模拟 subprocess.run 返回值
        def __init__(self, stdout):
            self.stdout = stdout

    def fake(args):
        # tasklist 参数形如 ['/FI', 'PID eq 123', '/NH'] 或 ['/FI', 'IMAGENAME eq xxx', '/NH']
        filt = args[1] if len(args) > 1 else ''
        if filt.startswith('PID eq'):
            pid = filt.split('eq', 1)[1].strip()
            if pid_map.get(pid):
                return _R(f'hermes-agent-cn-runtime-w   {pid} Console   1   100,000 K\r\n')
            return _R('信息: 没有运行的任务匹配指定的标准。\r\n')  # no tasks match
        if filt.startswith('IMAGENAME eq'):
            return _R(image_line if image_line else '信息: 没有运行的任务匹配指定的标准。\r\n')
        return _R('')
    return fake


DASH_CMD = (r'"D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18'
            r'\hermes-agent-cn-runtime-win32-x64.exe" dashboard --host 127.0.0.1 --port 9120 --no-open')
GW_CMD = (r'"D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18'
          r'\hermes-agent-cn-runtime-win32-x64.exe" gateway run')


class GatewayRunningTestBase(unittest.TestCase):

    def setUp(self):
        self.gk = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.new_pid_file = base / 'hermes-home' / 'gateway.pid'   # 新位置（部分启动上下文写这里）
        self.old_pid_file = base / 'gateway-runtime' / 'gateway.pid'  # 桌面App在场时网关写这里
        self.new_pid_file.parent.mkdir(parents=True)
        self.old_pid_file.parent.mkdir(parents=True)
        self.gk.GATEWAY_PID_FILES = [str(self.new_pid_file), str(self.old_pid_file)]

    def _write_pid(self, path, pid):
        path.write_text(json.dumps({
            'pid': pid, 'kind': 'hermes-gateway',
            'argv': ['x', 'gateway', 'run'], 'start_time': 1,
            'hermes_home': 'D:\\x',
        }), encoding='utf-8')


class TestIncident1FalseAlarm(GatewayRunningTestBase):
    """事故1：误报（旧位置死PID + 新位置活PID）。"""

    def test_stale_old_pid_new_location_alive(self):
        """旧位置死pid=10900、新位置活pid=109352 → 必须判活着。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self.gk._tasklist = _mk_tasklist({'10900': False, '109352': True})
        self.gk._wmic_processes = lambda: [('109352', GW_CMD)]
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'事故复现失败：{reason}')
        self.assertIn('109352', reason)

    def test_pid_alive_wmic_unavailable_trusts_pid_file(self):
        """wmic 查不到（不可用）→ PID 文件活着就信（PID文件由网关自己写，权威）。"""
        self._write_pid(self.new_pid_file, 109352)
        self.gk._tasklist = _mk_tasklist({'109352': True})
        self.gk._wmic_processes = lambda: []
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'{reason}')

    def test_corrupt_pid_file_falls_back(self):
        """PID 文件损坏（非JSON）→ 不抛异常，走命令行兜底。"""
        self.old_pid_file.write_text('not-json', encoding='utf-8')
        self.gk._tasklist = _mk_tasklist({})
        self.gk._wmic_processes = lambda: [('998877', GW_CMD)]
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'损坏文件导致兜底失效：{reason}')

    def test_only_new_location_file_alive(self):
        """只有一处 PID 文件且 PID 活 → 判活着。"""
        self._write_pid(self.new_pid_file, 109352)
        self.gk._tasklist = _mk_tasklist({'109352': True})
        self.gk._wmic_processes = lambda: [('109352', GW_CMD)]
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'{reason}')


class TestIncident2FalseSilence(GatewayRunningTestBase):
    """事故2：漏报（网关死了，dashboard 同名 exe 被误认成网关）。"""

    def test_dashboard_only_is_not_gateway(self):
        """PID文件全死/缺失 + 只剩 dashboard 同名进程 → 必须判死（修复2核心场景）。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self.gk._tasklist = _mk_tasklist({'10900': False, '109352': False})
        self.gk._wmic_processes = lambda: [('101920', DASH_CMD)]
        running, reason = self.gk.is_gateway_running()
        self.assertFalse(running, f'漏报复现失败（把dashboard当网关）：{reason}')

    def test_pid_alive_but_dashboard_argv_skipped(self):
        """PID 文件活着但命令行是 dashboard（如误写）→ 该文件不算数，继续找。"""
        self._write_pid(self.new_pid_file, 101920)  # dashboard 的 pid
        self.gk._tasklist = _mk_tasklist({'101920': True})
        self.gk._wmic_processes = lambda: [('101920', DASH_CMD)]
        running, _ = self.gk.is_gateway_running()
        self.assertFalse(running)

    def test_mixed_dashboard_and_gateway_alive(self):
        """dashboard 与真网关并存 → 判活且理由指向网关 pid。"""
        self.gk._tasklist = _mk_tasklist({})
        self.gk._wmic_processes = lambda: [('101920', DASH_CMD), ('108800', GW_CMD)]
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running)
        self.assertIn('108800', reason)

    def test_all_dead_no_process(self):
        """PID 全死、无任何进程 → 判死（保持原有能力，不误报活）。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self.gk._tasklist = _mk_tasklist({'10900': False, '109352': False})
        self.gk._wmic_processes = lambda: []
        running, _ = self.gk.is_gateway_running()
        self.assertFalse(running)


class TestMainSilentWhenAlive(unittest.TestCase):

    def setUp(self):
        self.gk = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        env_file = base / '.env'
        env_file.write_text('FEISHU_GROUP_POLICY=open\nFEISHU_REQUIRE_MENTION=false\n', encoding='utf-8')
        channel = base / 'channel_directory.json'
        channel.write_text(json.dumps({'platforms': {'feishu': [
            {'type': 'group', 'name': 'g'}]}}), encoding='utf-8')
        self.gk.ENV_FILE = str(env_file)
        self.gk.CHANNEL_DIR = str(channel)
        self.gk.STATE_FILE = str(base / 'cache' / 'state.json')
        self.gk.is_gateway_running = lambda: (True, 'pid=1 alive')

    def test_main_exit0_silent_when_alive(self):
        """网关活着+配置正常 → exit 0 且零输出（不发报警、不执行重启）。"""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.gk.main()
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().strip(), '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
