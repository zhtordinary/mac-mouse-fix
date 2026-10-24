#!/usr/bin/env python3
"""Exercise delivery with private Git repositories and inert SSH/build/install fixtures."""

import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mmf-delivery-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.mini, self.air = self.root / "mini", self.root / "air"
        self.origin = self.root / "origin.git"
        self.built = self.root / "built" / "Mac Mouse Fix.app"
        self.install_log, self.build_log = self.root / "installs", self.root / "builds"
        binaries = self.root / "bin"
        binaries.mkdir()
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GIT_", "BASH_FUNC_")) and key not in ("BASH_ENV", "ENV")
        }
        self.env.update(
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="Delivery Test", GIT_AUTHOR_EMAIL="delivery@example.invalid",
            GIT_COMMITTER_NAME="Delivery Test", GIT_COMMITTER_EMAIL="delivery@example.invalid",
            PATH=str(binaries) + os.pathsep + self.env["PATH"],
            INSTALL_LOG=str(self.install_log), BUILD_LOG=str(self.build_log),
            MINI_FIXTURE=str(self.mini), BUILT_APP=str(self.built), FIXTURE_ROOT=str(self.root),
        )
        (binaries / "bash").symlink_to("/bin/bash")
        self.executable(binaries / "ssh", f"#!{sys.executable}\n" + """
import os, sys
args = sys.argv[1:]
while args and args[0] == '-o':
    args = args[2:]
host, *parts = args
if host == os.environ.get('FAIL_PEER'):
    sys.exit(255)
assert host in ('macmini', 'macbook-air')
command = ' '.join(parts)
assert os.environ['FIXTURE_ROOT'] in command
os.execv('/bin/bash', ['bash', '-c', command])
""")
        self.executable(binaries / "xcodebuild", r"""#!/bin/sh
set -eu
printf 'build\n' >> "$BUILD_LOG"
git -C "$MINI_FIXTURE" rev-parse HEAD > "$BUILT_APP/Contents/build-source.txt"
""")
        (self.built / "Contents").mkdir(parents=True)
        self.git(self.root, "init", "--bare", str(self.origin))
        self.git(self.root, "init", "-b", "personal-use", str(self.mini))
        scripts = self.mini / "scripts"
        scripts.mkdir()
        text = Path(__file__).with_name("ai-deliver.sh").read_text()
        substitutions = {
            'MINI_REPO="/Users/zibuyu/Projects/mac-mouse-fix"': "MINI_REPO=" + shlex.quote(str(self.mini)),
            'AIR_REPO="/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix"': "AIR_REPO=" + shlex.quote(str(self.air)),
            'ORIGIN_URL="git@github.com:${GITHUB_REPO}.git"': "ORIGIN_URL=" + shlex.quote(self.origin.as_uri()),
            'local built_app="/Users/zibuyu/Library/Developer/Xcode/DerivedData/Mouse_Fix-ceeisowaynrxaeadqybxtuyqkyck/Build/Products/Release/Mac Mouse Fix.app"': "local built_app=" + shlex.quote(str(self.built)),
        }
        for old, new in substitutions.items():
            self.assertEqual(text.count(old), 1)
            text = text.replace(old, new)
        self.executable(scripts / "ai-deliver.sh", text)
        self.executable(scripts / "setup-app.sh", r"""#!/bin/sh
set -eu
printf '%s\n' "$(cd -- "$(dirname -- "$0")/.." && pwd)" >> "$INSTALL_LOG"
""")
        (self.mini / "AGENTS.md").write_text("base rules\n")
        (self.mini / "runtime.txt").write_text("base runtime\n")
        self.git(self.mini, "add", ".")
        self.git(self.mini, "commit", "-m", "base")
        self.git(self.mini, "remote", "add", "origin", self.origin.as_uri())
        self.git(self.mini, "push", "origin", "personal-use")
        self.git(self.root, "clone", "--branch", "personal-use", self.origin.as_uri(), str(self.air))

    @staticmethod
    def executable(path, text):
        path.write_text(text)
        path.chmod(0o755)

    def git(self, repo, *args):
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], env=self.env, text=True, stderr=subprocess.PIPE
        ).strip()

    def delivery(self, repo, *args, success=True):
        result = subprocess.run(
            ["/bin/bash", str(repo / "scripts/ai-deliver.sh"), *args],
            cwd=repo, env=self.env, text=True, capture_output=True,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        self.assertEqual("交付完成" in output, success, output)
        return output

    def docs(self, repo, success=True):
        (repo / "AGENTS.md").write_text(f"rules from {repo.name}\n")
        return self.delivery(repo, "--message", "docs: rules", "--files", "AGENTS.md", success=success)

    def synced(self):
        final = self.git(self.origin, "rev-parse", "refs/heads/personal-use")
        for repo in (self.mini, self.air):
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), final)
            self.assertEqual(self.git(repo, "status", "--porcelain=v1", "--untracked-files=all"), "")
        return final

    def no_app_actions(self):
        self.assertFalse(self.install_log.exists())
        self.assertFalse(self.build_log.exists())

    def test_docs_sync_in_both_directions_without_app_actions(self):
        for repo in (self.mini, self.air):
            with self.subTest(role=repo.name):
                self.assertIn("INSTALL=skipped", self.docs(repo))
                self.synced()
                self.no_app_actions()

    def test_document_resume_in_both_directions_does_not_recommit(self):
        for repo in (self.mini, self.air):
            with self.subTest(role=repo.name):
                (repo / "AGENTS.md").write_text(f"resume {repo.name}\n")
                self.git(repo, "add", "AGENTS.md")
                self.git(repo, "commit", "-m", "docs: resume fixture")
                self.git(repo, "push", "origin", "personal-use")
                sha = self.git(repo, "rev-parse", "HEAD")
                self.assertIn("INSTALL=skipped", self.delivery(repo, "--resume", sha))
                self.assertEqual(self.synced(), sha)
                self.no_app_actions()

    def test_runtime_build_and_separate_artifact_commit_in_both_directions(self):
        for index, repo in enumerate((self.mini, self.air), 1):
            with self.subTest(role=repo.name):
                (repo / "runtime.txt").write_text(f"runtime from {repo.name}\n")
                output = self.delivery(repo, "--message", "fix: runtime", "--files", "runtime.txt")
                receipt = re.search(r"Source SHA: ([0-9a-f]{40})", output)
                assert receipt is not None, output
                source = receipt.group(1)
                final = self.synced()
                self.assertNotEqual(source, final)
                self.assertEqual(self.git(repo, "rev-parse", final + "^"), source)
                paths = self.git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", final).splitlines()
                self.assertTrue(paths and all(p.startswith("releases/") for p in paths))
                self.assertEqual(len(self.build_log.read_text().splitlines()), index)
                installs = self.install_log.read_text().splitlines()
                for machine in (self.mini, self.air):
                    self.assertEqual(installs.count(str(machine)), index)

    def test_dirty_peer_is_preserved(self):
        (self.air / "AGENTS.md").write_text("foreign WIP\n")
        self.docs(self.mini, success=False)
        self.assertEqual((self.air / "AGENTS.md").read_text(), "foreign WIP\n")
        self.no_app_actions()

    def test_wrong_peer_branch_is_rejected(self):
        self.git(self.air, "switch", "-c", "other-task")
        self.docs(self.mini, success=False)
        self.assertEqual(self.git(self.air, "branch", "--show-current"), "other-task")
        self.no_app_actions()

    def test_wrong_peer_remote_is_rejected(self):
        other = (self.root / "unapproved.git").as_uri()
        self.git(self.air, "remote", "set-url", "origin", other)
        self.docs(self.mini, success=False)
        self.assertEqual(self.git(self.air, "remote", "get-url", "origin"), other)
        self.no_app_actions()

    def test_offline_peer_fails_and_resume_does_not_recommit(self):
        self.env["FAIL_PEER"] = "macbook-air"
        self.docs(self.mini, success=False)
        sha = self.git(self.mini, "rev-parse", "HEAD")
        del self.env["FAIL_PEER"]
        self.assertIn("INSTALL=skipped", self.delivery(self.mini, "--resume", sha))
        self.assertEqual(self.synced(), sha)
        self.no_app_actions()

    def test_resume_rejects_invalid_sha(self):
        self.delivery(self.mini, "--resume", "not-a-sha", success=False)
        self.no_app_actions()

    def test_resume_rejects_unpublished_source(self):
        (self.mini / "AGENTS.md").write_text("unpublished rules\n")
        self.git(self.mini, "add", "AGENTS.md")
        self.git(self.mini, "commit", "-m", "docs: unpublished")
        self.delivery(self.mini, "--resume", self.git(self.mini, "rev-parse", "HEAD"), success=False)
        self.no_app_actions()

    def test_doc_resume_does_not_take_unreviewed_remote_changes(self):
        (self.mini / "AGENTS.md").write_text("published rules\n")
        self.git(self.mini, "add", "AGENTS.md")
        self.git(self.mini, "commit", "-m", "docs: published")
        self.git(self.mini, "push", "origin", "personal-use")
        source = self.git(self.mini, "rev-parse", "HEAD")
        self.git(self.air, "fetch", "origin", "personal-use")
        self.git(self.air, "merge", "--ff-only", "origin/personal-use")
        (self.air / "runtime.txt").write_text("another task\n")
        self.git(self.air, "add", "runtime.txt")
        self.git(self.air, "commit", "-m", "fix: another task")
        self.git(self.air, "push", "origin", "personal-use")
        self.delivery(self.mini, "--resume", source, success=False)
        self.assertEqual(self.git(self.mini, "rev-parse", "HEAD"), source)
        self.no_app_actions()

    def test_unspecified_changes_fail_before_commit(self):
        original = self.git(self.mini, "rev-parse", "HEAD")
        (self.mini / "other.txt").write_text("preserve this\n")
        self.docs(self.mini, success=False)
        self.assertEqual(self.git(self.mini, "rev-parse", "HEAD"), original)
        self.assertEqual((self.mini / "other.txt").read_text(), "preserve this\n")
        self.no_app_actions()


if __name__ == "__main__":
    unittest.main(verbosity=2)
