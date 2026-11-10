#!/usr/bin/env python3
"""Exercise delivery gates with isolated Git and inert command fixtures.

The fixture guard, bare repository, SSH command, build command, and install
command exist only to test local control flow. They are not evidence about a
real Git hosting platform, Actions, webhooks, Git Apps, or external publishing.
"""

import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import unittest


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mmf-delivery-test-")
        self.addCleanup(self.cleanup_temporary)
        self.root = Path(self.temporary.name).resolve()
        self.mini, self.air = self.root / "mini", self.root / "air"
        self.origin = self.root / "origin.git"
        self.built = self.root / "built" / "Mac Mouse Fix.app"
        self.install_log = self.root / "installs"
        self.build_log = self.root / "builds"
        self.guard_log = self.root / "guard"
        self.ssh_log = self.root / "ssh"
        self.sources = {}
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
            GUARD_LOG=str(self.guard_log), SSH_LOG=str(self.ssh_log),
            MINI_FIXTURE=str(self.mini), FIXTURE_ROOT=str(self.root),
        )
        (binaries / "bash").symlink_to("/bin/bash")
        self.executable(binaries / "ssh", f"#!{sys.executable}\n" + """
import os, sys
args = sys.argv[1:]
while args and args[0] == '-o':
    args = args[2:]
host, *parts = args
with open(os.environ['SSH_LOG'], 'a', encoding='utf-8') as log:
    log.write(host + '\\n')
if host == os.environ.get('FAIL_PEER'):
    sys.exit(255)
assert host in ('macmini', 'macbook-air')
command = ' '.join(parts)
assert os.environ['FIXTURE_ROOT'] in command
os.execv('/bin/bash', ['bash', '-c', command])
""")
        self.executable(binaries / "xcodebuild", r"""#!/bin/sh
set -eu
mkdir -p "$BUILT_APP/Contents"
printf 'build\n' >> "$BUILD_LOG"
git -C "$MINI_FIXTURE" rev-parse HEAD > "$BUILT_APP/Contents/build-source.txt"
""")
        self.executable(binaries / "project-guard", r"""#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$GUARD_LOG"
printf 'fixture-handoff\n'
""")
        self.env["BUILT_APP"] = str(self.built)
        self.git(self.root, "init", "--bare", str(self.origin))
        self.git(self.root, "init", "-b", "personal-use", str(self.mini))
        scripts = self.mini / "scripts"
        scripts.mkdir()
        text = Path(__file__).with_name("ai-deliver.sh").read_text()
        # The fixture exercises both the local candidate path and the guarded
        # push path; it never models real platform authorization.
        guard = binaries / "project-guard"
        guard_setting = "PROJECT_GUARD=" + shlex.quote(str(guard))
        if self._testMethodName in {
            "test_push_request_requires_a_real_project_guard_before_commit",
            "test_resume_push_request_without_real_guard_still_blocks_before_fetch",
        }:
            guard_setting = "PROJECT_GUARD=''"
        substitutions = {
            'MINI_REPO="/Users/zibuyu/Projects/mac-mouse-fix"': "MINI_REPO=" + shlex.quote(str(self.mini)),
            'AIR_REPO="/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix"': "AIR_REPO=" + shlex.quote(str(self.air)),
            'ORIGIN_URL="git@github.com:${GITHUB_REPO}.git"': "ORIGIN_URL=" + shlex.quote(self.origin.as_uri()),
            "PROJECT_GUARD=''": guard_setting,
            'local built_app="/Users/zibuyu/Library/Developer/Xcode/DerivedData/Mouse_Fix-ceeisowaynrxaeadqybxtuyqkyck/Build/Products/Release/Mac Mouse Fix.app"': "local built_app=" + shlex.quote(str(self.built)),
        }
        for old, new in substitutions.items():
            self.assertEqual(text.count(old), 1)
            text = text.replace(old, new)
        self.executable(scripts / "ai-deliver.sh", text)
        self.executable(self.mini / "scripts/setup-app.sh", r"""#!/bin/sh
set -eu
[ "$#" -eq 1 ] && [ "$1" = "--with-app" ]
printf '%s\n' "$(cd -- "$(dirname -- "$0")/.." && pwd)" >> "$INSTALL_LOG"
""")
        (self.mini / "AGENTS.md").write_text("base rules\n")
        (self.mini / "runtime.txt").write_text("base runtime\n")
        self.git(self.mini, "add", ".")
        self.git(self.mini, "commit", "-m", "base")
        self.git(self.mini, "remote", "add", "origin", self.origin.as_uri())
        base = self.git(self.mini, "rev-parse", "HEAD")
        # Seed the isolated bare fixture without exercising a real Git push.
        self.git(self.origin, "fetch", str(self.mini), f"{base}:refs/heads/personal-use")
        self.git(self.root, "clone", "--branch", "personal-use", self.origin.as_uri(), str(self.air))

    def cleanup_temporary(self):
        root = self.root
        self.temporary.cleanup()
        self.assertFalse(root.exists(), root)

    @staticmethod
    def executable(path, text):
        path.write_text(text)
        path.chmod(0o755)

    def git(self, repo, *args):
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], env=self.env, text=True, stderr=subprocess.PIPE
        ).strip()

    def source_for(self, repo):
        role = repo.name
        if role not in self.sources:
            source = self.root / f"task-{role}"
            self.git(repo, "worktree", "add", "-b", f"task-{role}", str(source), "HEAD")
            self.sources[role] = source
        return self.sources[role]

    def run_script(self, repo, *args):
        process = subprocess.Popen(
            ["/bin/bash", str(repo / "scripts/ai-deliver.sh"), *args],
            cwd=repo,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        process_group = os.getpgid(process.pid)
        if process_group != process.pid:
            process.kill()
            process.wait()
            raise AssertionError("delivery fixture did not create an isolated process group")
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired as error:
            self._terminate_process_group(process, process_group)
            raise AssertionError("delivery fixture timed out after 30 seconds") from error
        return subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout,
            stderr,
        )

    @staticmethod
    def _terminate_process_group(process, process_group):
        for termination_signal in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process_group, termination_signal)
            except ProcessLookupError:
                process.communicate(timeout=5)
                return
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                continue
            try:
                os.killpg(process_group, 0)
            except ProcessLookupError:
                return
        raise AssertionError("delivery fixture process group did not exit after bounded cleanup")

    @staticmethod
    def output(result):
        return result.stdout + result.stderr

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("交付完成", self.output(result))

    def assert_blocked(self, result, marker):
        self.assertNotEqual(result.returncode, 0, self.output(result))
        self.assertIn(marker, self.output(result))

    def no_app_actions(self):
        self.assertFalse(self.install_log.exists())
        self.assertFalse(self.build_log.exists())

    def no_ssh(self):
        self.assertFalse(self.ssh_log.exists())

    def synced(self):
        final = self.git(self.origin, "rev-parse", "refs/heads/personal-use")
        for repo in (self.mini, self.air):
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), final)
            self.assertEqual(self.git(repo, "status", "--porcelain=v1", "--untracked-files=all"), "")
        return final

    def commit_source(self, source, path="runtime.txt", message="source candidate"):
        self.git(source, "add", path)
        self.git(source, "commit", "-m", message)
        return self.git(source, "rev-parse", "HEAD")

    def install_hook(self, source, name, body):
        hook_dir = self.root / f"hooks-{name}"
        hook_dir.mkdir()
        hook = hook_dir / "pre-commit"
        self.executable(hook, "#!/bin/sh\nset -eu\n" + body)
        self.git(source, "config", "core.hooksPath", str(hook_dir))

    def install_main_post_commit_hook(self, repo, name, body):
        hook_dir = self.root / f"main-hooks-{name}"
        hook_dir.mkdir()
        hook = hook_dir / "post-commit"
        self.executable(hook, "#!/bin/sh\nset -eu\n" + body)
        self.git(repo, "config", "core.hooksPath", str(hook_dir))

    def accept_source_in_fixture_remote(self, source, sha):
        # This models an already accepted SHA for recovery control flow only.
        self.git(self.origin, "fetch", str(source), f"{sha}:refs/heads/personal-use")

    def test_local_candidate_is_saved_without_external_side_effects(self):
        source = self.source_for(self.mini)
        (source / "AGENTS.md").write_text("source candidate\n")
        result = self.run_script(source, "--message", "docs: candidate", "--files", "AGENTS.md")
        self.assert_blocked(result, "PUSH=blocked")
        candidate = self.git(source, "rev-parse", "HEAD")
        self.assertNotEqual(candidate, self.git(self.mini, "rev-parse", "HEAD"))
        self.assertEqual(self.git(self.origin, "rev-parse", "refs/heads/personal-use"), self.git(self.mini, "rev-parse", "HEAD"))
        self.assertFalse(self.guard_log.exists())
        self.no_ssh()
        self.no_app_actions()
    def test_default_docs_and_runtime_candidates_are_saved_locally_but_push_is_blocked(self):
        for repo in (self.mini, self.air):
            with self.subTest(role=repo.name):
                source = self.source_for(repo)
                (source / "AGENTS.md").write_text(f"rules from {repo.name}\n")
                result = self.run_script(source, "--message", "docs: rules", "--files", "AGENTS.md")
                self.assert_blocked(result, "PUSH=blocked")
                self.assertNotEqual(self.git(source, "rev-parse", "HEAD"), self.git(self.mini, "rev-parse", "HEAD"))
                self.assertIn("SOURCE_SHA=", self.output(result))
                self.assertEqual(self.git(self.origin, "rev-parse", "refs/heads/personal-use"), self.git(self.mini, "rev-parse", "HEAD"))
                self.no_app_actions()
                self.no_ssh()

    def test_runtime_path_does_not_infer_build_or_install(self):
        source = self.source_for(self.mini)
        (source / "runtime.txt").write_text("runtime candidate\n")
        result = self.run_script(source, "--message", "fix: runtime", "--files", "runtime.txt")
        self.assert_blocked(result, "PUSH=blocked")
        self.no_app_actions()
        self.no_ssh()

    def test_with_app_does_not_bypass_push_gate(self):
        source = self.source_for(self.mini)
        (source / "runtime.txt").write_text("runtime candidate\n")
        result = self.run_script(source, "--with-app", "--message", "fix: runtime", "--files", "runtime.txt")
        self.assert_blocked(result, "PUSH=blocked")
        self.no_app_actions()
        self.no_ssh()

    def test_push_request_requires_a_real_project_guard_before_commit(self):
        source = self.source_for(self.mini)
        (source / "AGENTS.md").write_text("requested push\n")
        original = self.git(source, "rev-parse", "HEAD")
        result = self.run_script(
            source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md"
        )
        self.assert_blocked(result, "未配置真实项目副作用守卫")
        self.assertEqual(self.git(source, "rev-parse", "HEAD"), original)
        self.no_app_actions()
        self.no_ssh()

    def test_resume_same_sha_requires_external_pending_state_review_before_fetch(self):
        source = self.source_for(self.mini)
        (source / "runtime.txt").write_text("accepted source\n")
        sha = self.commit_source(source)
        self.git(source, "fetch", "origin", "personal-use")
        self.accept_source_in_fixture_remote(source, sha)
        tracking_before = self.git(source, "rev-parse", "refs/remotes/origin/personal-use")
        result = self.run_script(source, "--resume", sha)
        self.assert_blocked(result, "普通 Git push 及其外部触发默认阻塞")
        self.assertEqual(self.git(source, "rev-parse", "refs/remotes/origin/personal-use"), tracking_before)
        self.no_app_actions()
        self.no_ssh()

    def test_resume_push_request_without_real_guard_still_blocks_before_fetch(self):
        source = self.source_for(self.mini)
        (source / "runtime.txt").write_text("accepted source\n")
        sha = self.commit_source(source)
        self.git(source, "fetch", "origin", "personal-use")
        self.accept_source_in_fixture_remote(source, sha)
        tracking_before = self.git(source, "rev-parse", "refs/remotes/origin/personal-use")
        result = self.run_script(source, "--request-push-effects", "--resume", sha)
        self.assert_blocked(result, "未配置真实项目副作用守卫")
        self.assertEqual(self.git(source, "rev-parse", "refs/remotes/origin/personal-use"), tracking_before)
        self.no_app_actions()
        self.no_ssh()

    def test_build_remote_requires_push_request_and_app_authorization(self):
        sha = self.git(self.mini, "rev-parse", "HEAD")
        result = self.run_script(self.mini, "--build-remote", sha, "--with-app")
        self.assert_blocked(result, "--build-remote 必须同时提供真实 guard HANDOFF")
        self.no_app_actions()
        self.no_ssh()

    def test_unlisted_worktree_changes_are_preserved_before_candidate_commit(self):
        source = self.source_for(self.mini)
        original = self.git(source, "rev-parse", "HEAD")
        (source / "other.txt").write_text("preserve this\n")
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "指定的文件列表与当前工作树修改不符")
        self.assertEqual(self.git(source, "rev-parse", "HEAD"), original)
        self.assertEqual((source / "other.txt").read_text(), "preserve this\n")
        self.no_app_actions()
        self.no_ssh()

    def test_pre_commit_extra_file_is_blocked_before_push(self):
        source = self.source_for(self.mini)
        self.install_hook(source, "extra", 'repo=$(git rev-parse --show-toplevel)\nprintf extra > "$repo/README.md"\ngit -C "$repo" add README.md\n')
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "commit hook 改变了固定源码候选 tree")
        self.assertEqual(self.git(self.origin, "rev-parse", "refs/heads/personal-use"), self.git(self.mini, "rev-parse", "HEAD"))
        self.no_app_actions()
        self.no_ssh()

    def test_pre_commit_rewrite_of_selected_file_is_blocked_before_push(self):
        source = self.source_for(self.mini)
        self.install_hook(source, "rewrite", 'repo=$(git rev-parse --show-toplevel)\nprintf rewritten > "$repo/AGENTS.md"\ngit -C "$repo" add AGENTS.md\n')
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "commit hook 改变了固定源码候选 tree")
        self.assertEqual(self.git(self.origin, "rev-parse", "refs/heads/personal-use"), self.git(self.mini, "rev-parse", "HEAD"))
        self.no_app_actions()
        self.no_ssh()

    def test_explicit_docs_sync_in_both_directions_with_fixture_guard(self):
        for repo in (self.mini, self.air):
            with self.subTest(role=repo.name):
                source = self.source_for(repo)
                (source / "AGENTS.md").write_text(f"rules from {repo.name}\n")
                result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
                self.assert_success(result)
                self.assertEqual(self.synced(), self.git(source, "rev-parse", "HEAD"))
                self.no_app_actions()

    def test_artifact_post_commit_parent_drift_blocks_before_push(self):
        hook_count = self.root / "artifact-post-commit-count"
        inner_hooks = self.root / "artifact-inner-hooks"
        quoted_count = shlex.quote(str(hook_count))
        quoted_inner_hooks = shlex.quote(str(inner_hooks))
        self.install_main_post_commit_hook(
            self.mini,
            "drift",
            f'''if [ "$(git branch --show-current)" = "personal-use" ]; then
  count=0
  if [ -f {quoted_count} ]; then count=$(cat {quoted_count}); fi
  count=$((count + 1))
  printf '%s\\n' "$count" > {quoted_count}
  if [ "$count" -eq 1 ]; then
    mkdir -p {quoted_inner_hooks}
    git -c core.hooksPath={quoted_inner_hooks} commit --allow-empty --no-verify -m hook-empty
  fi
fi
''',
        )
        source = self.source_for(self.mini)
        (source / "runtime.txt").write_text("runtime with hook drift\n")
        result = self.run_script(source, "--request-push-effects", "--with-app", "--message", "fix: runtime", "--files", "runtime.txt")
        self.assert_blocked(result, "产物候选父提交漂移")
        self.assertEqual(hook_count.read_text().strip(), "1")
        self.assertEqual(
            self.git(self.mini, "rev-list", "--count", "--all", "--grep=^hook-empty$"),
            "1",
        )
        origin_head = self.git(self.origin, "rev-parse", "refs/heads/personal-use")
        self.assertEqual(self.git(source, "rev-parse", "HEAD"), origin_head)
        self.assertNotIn("releases/", self.git(self.origin, "ls-tree", "-r", "--name-only", origin_head))

    def test_explicit_runtime_build_and_artifacts_in_both_directions_with_fixture_guard(self):
        for index, repo in enumerate((self.mini, self.air), 1):
            with self.subTest(role=repo.name):
                source = self.source_for(repo)
                (source / "runtime.txt").write_text(f"runtime from {repo.name}\n")
                result = self.run_script(source, "--request-push-effects", "--with-app", "--message", "fix: runtime", "--files", "runtime.txt")
                self.assert_success(result)
                source_sha = self.git(source, "rev-parse", "HEAD")
                final = self.synced()
                self.assertNotEqual(source_sha, final)
                self.assertEqual(self.git(repo, "rev-parse", final + "^"), source_sha)
                paths = self.git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", final).splitlines()
                self.assertTrue(paths and all(path.startswith("releases/") for path in paths))
                self.assertEqual(len(self.build_log.read_text().splitlines()), index)
                installs = self.install_log.read_text().splitlines()
                for machine in (self.mini, self.air):
                    self.assertEqual(installs.count(str(machine)), index)

    def test_explicit_document_resume_does_not_recommit_source_both_directions(self):
        for repo in (self.mini, self.air):
            with self.subTest(role=repo.name):
                source = self.source_for(repo)
                (source / "AGENTS.md").write_text(f"resume {repo.name}\n")
                sha = self.commit_source(source, path="AGENTS.md", message="docs: resume")
                self.accept_source_in_fixture_remote(source, sha)
                result = self.run_script(source, "--request-push-effects", "--resume", sha)
                self.assert_success(result)
                self.assertEqual(self.synced(), sha)
                self.no_app_actions()

    def test_explicit_runtime_resume_app_stage_does_not_recommit_source(self):
        for index, repo in enumerate((self.mini, self.air), 1):
            with self.subTest(role=repo.name):
                source = self.source_for(repo)
                (source / "runtime.txt").write_text(f"resume {repo.name}\n")
                sha = self.commit_source(source)
                self.accept_source_in_fixture_remote(source, sha)
                result = self.run_script(source, "--request-push-effects", "--with-app", "--resume", sha)
                self.assert_success(result)
                final = self.synced()
                self.assertNotEqual(final, sha)
                self.assertEqual(self.git(repo, "rev-parse", final + "^"), sha)
                self.assertEqual(len(self.build_log.read_text().splitlines()), index)

    def test_dirty_peer_is_preserved(self):
        source = self.source_for(self.mini)
        (self.air / "AGENTS.md").write_text("foreign WIP\n")
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "对端存在未提交修改")
        self.assertEqual((self.air / "AGENTS.md").read_text(), "foreign WIP\n")
        self.no_app_actions()

    def test_wrong_peer_branch_is_rejected(self):
        source = self.source_for(self.mini)
        self.git(self.air, "switch", "-c", "other-task")
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "对端分支不符")
        self.assertEqual(self.git(self.air, "branch", "--show-current"), "other-task")
        self.no_app_actions()

    def test_wrong_peer_remote_is_rejected(self):
        source = self.source_for(self.mini)
        other = (self.root / "unapproved.git").as_uri()
        self.git(self.air, "remote", "set-url", "origin", other)
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assert_blocked(result, "对端 remote 不符")
        self.assertEqual(self.git(self.air, "remote", "get-url", "origin"), other)
        self.no_app_actions()

    def test_offline_peer_fails_and_explicit_resume_does_not_recommit(self):
        source = self.source_for(self.mini)
        self.env["FAIL_PEER"] = "macbook-air"
        (source / "AGENTS.md").write_text("rules\n")
        result = self.run_script(source, "--request-push-effects", "--message", "docs: rules", "--files", "AGENTS.md")
        self.assertNotEqual(result.returncode, 0, self.output(result))
        sha = self.git(source, "rev-parse", "HEAD")
        del self.env["FAIL_PEER"]
        result = self.run_script(source, "--request-push-effects", "--resume", sha)
        self.assert_success(result)
        self.assertEqual(self.synced(), sha)
        self.no_app_actions()

    def test_resume_rejects_invalid_sha(self):
        source = self.source_for(self.mini)
        result = self.run_script(source, "--request-push-effects", "--resume", "not-a-sha")
        self.assert_blocked(result, "SOURCE_SHA 无效")
        self.no_app_actions()

    def test_resume_rejects_unpublished_source(self):
        source = self.source_for(self.mini)
        (source / "AGENTS.md").write_text("unpublished rules\n")
        sha = self.commit_source(source, path="AGENTS.md", message="docs: unpublished")
        result = self.run_script(source, "--request-push-effects", "--resume", sha)
        self.assert_blocked(result, "SOURCE_SHA 必须已发布到目标分支")
        self.no_app_actions()

    def test_resume_does_not_take_unreviewed_remote_changes(self):
        source = self.source_for(self.mini)
        (source / "AGENTS.md").write_text("published rules\n")
        sha = self.commit_source(source, path="AGENTS.md", message="docs: published")
        self.accept_source_in_fixture_remote(source, sha)
        self.git(self.air, "fetch", "origin", "personal-use")
        self.git(self.air, "merge", "--ff-only", "origin/personal-use")
        (self.air / "runtime.txt").write_text("another task\n")
        other_sha = self.commit_source(self.air, path="runtime.txt", message="fix: another task")
        self.git(self.origin, "fetch", str(self.air), f"{other_sha}:refs/heads/personal-use")
        result = self.run_script(source, "--request-push-effects", "--resume", sha)
        self.assert_blocked(result, "SOURCE_SHA 之后存在未授权的远端提交")
        self.assertEqual(self.git(source, "rev-parse", "HEAD"), sha)
        self.no_app_actions()


if __name__ == "__main__":
    unittest.main(verbosity=2)
