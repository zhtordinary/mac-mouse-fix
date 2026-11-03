#!/usr/bin/env python3
"""Verify setup-app fails closed without a trusted production verifier."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SetupAppSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mmf-setup-app-test-")
        self.addCleanup(self.cleanup_temporary)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.apps = self.root / "Applications"
        (self.repo / "scripts").mkdir(parents=True)
        self.apps.mkdir()
        self.setup_script = self.repo / "scripts" / "setup-app.sh"
        shutil.copy2(ROOT / "scripts/setup-app.sh", self.setup_script)
        self.setup_script.chmod(0o755)

    def cleanup_temporary(self):
        root = self.root
        self.temporary.cleanup()
        self.assertFalse(root.exists(), root)

    def make_object(self, name, content):
        path = self.apps / name
        path.write_text(content)
        return path

    def run_setup(self):
        return subprocess.run(
            [str(self.setup_script), "--with-app"],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def test_direct_entry_rejects_before_touching_existing_object(self):
        target = self.make_object("Mac Mouse Fix.app", "existing")
        result = self.run_setup()
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(target.read_text(), "existing")
        self.assertFalse((self.repo / "releases").exists())

    def test_direct_entry_rejects_without_creating_install_root_objects(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(list(self.apps.iterdir()), [])

    def test_test_mode_environment_cannot_enable_a_bypass(self):
        env = dict(**__import__("os").environ, MMF_INSTALL_TEST_MODE="1", MMF_INSTALL_ROOT=str(self.apps))
        result = subprocess.run(
            [str(self.setup_script), "--with-app"],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(list(self.apps.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
