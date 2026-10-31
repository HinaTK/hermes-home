# -*- coding: utf-8 -*-
"""TDD：网关守护误报（2026-10-31 真实事故，连续 70 次误报）。

事故回放：
- 10-31 04:09 网关被外部杀掉后重启（已知的 2-6 天不定期外部 kill 模式），
  新实例 pid=109352 把 PID 文件写到了 **新位置** hermes-home/gateway.pid；
- gateway_keeper.py 仍只读 **旧位置** data/gateway-runtime/gateway.pid（死 pid=10900，
  10-26 旧实例残留），判定"网关未运行"；
- 且 is_gateway_running 逻辑缺陷：PID 文件存在但 PID 已死时直接 return False，
  根本走不到按进程名兜底（兜底只在 PID 文件缺失时触发）；
- 每次误报还附带执行一次 hermes gateway start（返回0因为网关实际活着），
  然后复查旧 PID 文件依旧死 → 报警 → 连续 70 次推飞书（约 5.8 小时）。

修复语义：
1. PID 文件检查覆盖新旧两个位置（新位置优先）：任一文件的 PID 活着 = 网关活着；
2. 所有 PID 文件都死/解析失败时，按进程名兜底（与 PID 文件缺失时同等待遇）；
3. 网关活着时 main() 完全静默（exit 0 无输出），不发报警。
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


class TestGatewayRunning(unittest.TestCase):

    def setUp(self):
        self.gk = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.new_pid_file = base / 'hermes-home' / 'gateway.pid'   # 新位置（10-31 起网关写这里）
        self.old_pid_file = base / 'gateway-runtime' / 'gateway.pid'  # 旧位置（残留）
        self.new_pid_file.parent.mkdir(parents=True)
        self.old_pid_file.parent.mkdir(parents=True)

    def _write_pid(self, path, pid):
        path.write_text(json.dumps({
            'pid': pid, 'kind': 'hermes-gateway',
            'argv': ['x', 'gateway', 'run'], 'start_time': 1,
            'hermes_home': 'D:\\x',
        }), encoding='utf-8')

    def _point_module_to_tmp(self):
        self.gk.GATEWAY_PID_FILES = [str(self.new_pid_file), str(self.old_pid_file)]

    def test_incident_20261031_stale_old_pid_new_location_alive(self):
        """事故主场景：旧位置死pid=10900、新位置活pid=109352 → 必须判活着。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self._point_module_to_tmp()
        self.gk._tasklist = _mk_tasklist({'10900': False, '109352': True})
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'事故复现失败：{reason}')
        self.assertIn('109352', reason)

    def test_all_pid_files_dead_falls_back_to_image_name(self):
        """缺陷2：PID文件全死但进程名查得到 → 兜底必须生效（旧代码直接判死）。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self._point_module_to_tmp()
        self.gk._tasklist = _mk_tasklist(
            {'10900': False, '109352': False},
            image_line='hermes-agent-cn-runtime-w   998877 Console   1   100,000 K\r\n',
        )
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'兜底未生效：{reason}')
        self.assertIn('998877', reason)

    def test_only_new_location_file_alive(self):
        """只有新位置文件（旧位置文件不存在）且 PID 活 → 判活着。"""
        self._write_pid(self.new_pid_file, 109352)
        self._point_module_to_tmp()
        self.gk._tasklist = _mk_tasklist({'109352': True})
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'{reason}')

    def test_all_dead_no_process(self):
        """PID 全死且进程名也查无 → 判死（保持原有能力，不误报活）。"""
        self._write_pid(self.old_pid_file, 10900)
        self._write_pid(self.new_pid_file, 109352)
        self._point_module_to_tmp()
        self.gk._tasklist = _mk_tasklist({'10900': False, '109352': False})
        running, reason = self.gk.is_gateway_running()
        self.assertFalse(running)

    def test_corrupt_pid_file_falls_back(self):
        """PID 文件损坏（非JSON）→ 不得抛异常，走进程名兜底。"""
        self.old_pid_file.write_text('not-json', encoding='utf-8')
        self._point_module_to_tmp()
        self.gk._tasklist = _mk_tasklist(
            {},
            image_line='hermes-agent-cn-runtime-w   998877 Console   1   100,000 K\r\n',
        )
        running, reason = self.gk.is_gateway_running()
        self.assertTrue(running, f'损坏文件导致兜底失效：{reason}')


class TestMainSilentWhenAlive(unittest.TestCase):

    def setUp(self):
        self.gk = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        # env / channel / state 全部指向临时文件，避免依赖本机真实配置
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
