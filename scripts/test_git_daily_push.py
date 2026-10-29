#!/usr/bin/env python3
"""git_daily_push.py 秘密守卫测试（TDD：先写失败测试）。

背景（2026-10-29 事故）：git_daily_push.py 用 git add -A，把含 OpenRouter key 的
backups/config/config.yaml.good.* 卷进提交，连续 7 晚被 GitHub Push Protection 拒收。
守卫要求：add 之后、commit 之前扫描暂存区，命中秘密模式即中止该仓库并 unstage。
"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import git_daily_push as gdp


FAKE_OR_KEY = "sk-or-v1-" + "a" * 40
FAKE_ANT_KEY = "sk-ant-api03-" + "b" * 40
FAKE_GHP = "ghp_" + "c" * 36


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
    return r.returncode, r.stdout, r.stderr


class TestFindSecrets(unittest.TestCase):
    """模式识别单元测试。"""

    def test_detects_openrouter_key(self):
        hits = gdp.find_secrets(f"api_key: {FAKE_OR_KEY}")
        self.assertEqual(len(hits), 1)
        self.assertIn("OpenRouter", hits[0][0])
        # 不得泄露完整秘密到日志
        self.assertNotIn(FAKE_OR_KEY, hits[0][1])

    def test_detects_anthropic_github_aws_slack_refresh(self):
        for token, expect in [
            (FAKE_ANT_KEY, "Anthropic"),
            (FAKE_GHP, "GitHub"),
            ("AKIA" + "D" * 16, "AWS"),
            ("AIza" + "E" * 33, "Google"),
            ("xoxb-" + "F" * 20, "Slack"),
            ('"refresh_token": "rt_' + "g" * 40 + '"', "Refresh"),
        ]:
            hits = gdp.find_secrets(f"x {token} y")
            self.assertTrue(hits, f"未检出: {expect}")

    def test_ignores_placeholders_and_short_strings(self):
        for text in [
            "api_key: sk-or-v1-REDACTED",
            "api_key: ${OPENROUTER_KEY}",
            "sk-or-v1-",  # 空主体
            "ghp_short",
            "你的 refresh_token 会自动轮换",
        ]:
            self.assertEqual(gdp.find_secrets(text), [], f"误报: {text}")


class TestStagedSecretHits(unittest.TestCase):
    """暂存区扫描集成测试（真实临时 git 仓库，不联网）。"""

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="gdp_test_")
        _run("git init -q", self.repo)
        _run("git config user.email t@t", self.repo)
        _run("git config user.name t", self.repo)
        # 基线提交
        with open(os.path.join(self.repo, "base.txt"), "w") as f:
            f.write("clean\n")
        _run("git add base.txt && git commit -qm base", self.repo)

    def test_staged_secret_detected(self):
        with open(os.path.join(self.repo, "leak.txt"), "w") as f:
            f.write(f"key: {FAKE_OR_KEY}\n")
        _run("git add leak.txt", self.repo)
        hits = gdp.staged_secret_hits(self.repo)
        self.assertTrue(hits, "暂存区含 key 却未检出")

    def test_clean_stage_passes(self):
        with open(os.path.join(self.repo, "ok.txt"), "w") as f:
            f.write("just normal text 12345\n")
        _run("git add ok.txt", self.repo)
        self.assertEqual(gdp.staged_secret_hits(self.repo), [])

    def test_committed_unchanged_secret_not_flagged(self):
        # 已提交且无改动的文件不进 diff --cached，不重复报警（守卫只拦新增内容）
        with open(os.path.join(self.repo, "old.txt"), "w") as f:
            f.write(f"key: {FAKE_OR_KEY}\n")
        _run("git add old.txt && git commit -qm old", self.repo)
        self.assertEqual(gdp.staged_secret_hits(self.repo), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
