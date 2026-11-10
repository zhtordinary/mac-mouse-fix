#!/usr/bin/env python3
"""Regression checks for the project-owned collaboration and AOCI contract."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts/scan-root-empty.py"


class CollaborationContractTests(unittest.TestCase):
    def test_project_rules_point_to_the_local_contract(self):
        agents = (ROOT / "AGENTS.md").read_text()
        workflow = (ROOT / "docs/collaboration.md").read_text()
        ignore = (ROOT / ".gitignore").read_text()

        self.assertIn("docs/collaboration.md", agents)
        self.assertIn("github-repo-ops 2026.11.03.3", agents)
        self.assertIn("github-repo-ops 2026.11.03.3", workflow)
        self.assertIn("git@github.com:zhtordinary/mac-mouse-fix.git", workflow)
        self.assertIn("personal-use", workflow)
        self.assertIn("/.worktrees/", ignore)
        self.assertIn("AOCI 不适用/未接入", workflow)
        self.assertIn('`--repo "$TASK"`', workflow)
        self.assertIn("runtime_repository_root", workflow)
        self.assertIn("不创建伪 index", workflow)

    def test_future_governance_checks_actual_interfaces_and_each_candidate(self):
        workflow = (ROOT / "docs/collaboration.md").read_text()
        for requirement in (
            "两种接口均使用时分别核验",
            "不得假定 CLI 支持所有 MCP 操作",
            "session cwd 与任务树是不同上下文，不要求相等",
            "受管源码-only 候选即使正式资产未变也不能跳过治理",
            "范围未知即阻塞",
            "Verify、Check、实时 Guide",
            "保留工具的 CAS 检查与用户数据保护",
            "离线替身或静态文档不是实际治理证明",
        ):
            self.assertIn(requirement, workflow)

    def test_delivery_defaults_are_git_only_and_app_is_explicit(self):
        delivery = (ROOT / "scripts/ai-deliver.sh").read_text()
        setup = (ROOT / "scripts/setup-app.sh").read_text()
        for requirement in (
            "独立任务 worktree",
            "--with-app",
            "--build-remote 必须同时提供真实 guard HANDOFF",
            "--request-push-effects",
            "assert_external_push_guard",
            "AUTHORIZED_TREE",
            "verify_candidate_tree",
            "verify_artifact_candidate",
            "GUARD_HANDOFF",
            "--with-git-push",
            "--confirm-external-automation",
            "PUSH=blocked",
            "PUSH=blocked",
            "App 阶段未授权",
            "assert_release_only_descendant",
            "refs/heads/$TARGET_BRANCH",
        ):
            self.assertIn(requirement, delivery)
        self.assertNotIn("paths_require_build", delivery)
        self.assertIn("App 安装/重启必须显式提供 --with-app", setup)
        workflow = (ROOT / "docs/collaboration.md").read_text()
        self.assertIn("普通 Git push 不是纯本地 Git 操作", workflow)
        self.assertIn("真实外部未决状态", workflow)
        self.assertIn("--confirm-external-automation", workflow)
        self.assertIn("commit hook 插入额外文件", workflow)
        self.assertIn("`setup-app.sh` 当前在任何文件或进程操作前无条件拒绝", workflow)
        self.assertIn("保存本地候选", workflow)
        self.assertIn("各自明确授权", workflow)

    def test_local_development_does_not_claim_delivery_is_available(self):
        agents = (ROOT / "AGENTS.md").read_text()
        workflow = (ROOT / "docs/collaboration.md").read_text()
        self.assertIn("不因缺少远端 verifier 阻断本地开发", agents)
        self.assertIn("2026.11.05.2", workflow)
        self.assertIn("a24a0e07eb75faafac0f824091e705e2aab05bc9", workflow)
        self.assertIn("已核验的本地 remote-tracking SHA 只作为开发基线", workflow)
        self.assertIn("不是远端最新状态证明", workflow)
        self.assertIn("不得手动提交绕过现行门禁", workflow)
        self.assertIn("--confirm-external-automation", workflow)

    def test_worktree_ignore_rule_is_active(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", ".worktrees/ignore-check"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_aoci_formal_assets_are_not_created_without_project_contract(self):
        workflow = (ROOT / "docs/collaboration.md").read_text()
        for marker in ("aoci.txt", "aoci.code.txt", "aoci.meta.txt", ".aoci"):
            self.assertFalse((ROOT / marker).exists(), marker)
        self.assertIn("不运行 `init`", workflow)
        self.assertIn("不借用主 checkout/其他项目的服务", workflow)

    def test_root_scanner_is_one_level_read_only_and_symlink_safe(self):
        with tempfile.TemporaryDirectory(prefix="mmf-collaboration-test-") as directory:
            root = Path(directory)
            empty = root / "empty-directory"
            empty.mkdir()
            zero = root / "zero-byte"
            zero.touch()
            nonempty = root / "nonempty"
            nonempty.mkdir()
            (nonempty / "child").write_text("content")
            nested = root / "nested"
            nested.mkdir()
            (nested / "empty-child").mkdir()
            symlink = root / "empty-link"
            symlink.symlink_to(empty, target_is_directory=True)

            result = subprocess.run(
                [sys.executable, "-B", str(SCANNER), str(root)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["errors"], [])
            self.assertEqual(
                {(Path(item["path"]).name, item["kind"]) for item in payload["candidates"]},
                {("empty-directory", "empty_directory"), ("zero-byte", "zero_byte_file")},
            )
            self.assertTrue(empty.is_dir())
            self.assertTrue(zero.exists())
            self.assertTrue(symlink.is_symlink())
            self.assertTrue((nested / "empty-child").is_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
