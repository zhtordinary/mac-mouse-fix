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
        self.assertIn("github-repo-ops 2026.11.01.1", workflow)
        self.assertIn("git@github.com:zhtordinary/mac-mouse-fix.git", workflow)
        self.assertIn("personal-use", workflow)
        self.assertIn("/.worktrees/", ignore)
        self.assertIn("AOCI 不适用/未接入", workflow)
        self.assertIn('`--repo "$TASK"`', workflow)
        self.assertIn("runtime_repository_root", workflow)
        self.assertIn("不创建伪 index", workflow)

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
