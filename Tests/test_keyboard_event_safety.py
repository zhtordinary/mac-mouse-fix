#!/usr/bin/env python3
"""Execute the production null-safe keyboard event boundary with inert fakes."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ROOT / "Helper/Core/Actions/Actions.m"
SAFETY_HEADER = ROOT / "Helper/Core/Actions/KeyboardEventSafety.h"


HARNESS = r'''
#include "Helper/Core/Actions/KeyboardEventSafety.h"
#include <stdio.h>

static int created;
static int set_count;
static int post_count;
static int release_count;
static int token;

static void *null_create(uint16_t keyCode, bool keyDown) {
    (void)keyCode; (void)keyDown; created += 1; return NULL;
}
static void *valid_create(uint16_t keyCode, bool keyDown) {
    (void)keyCode; (void)keyDown; created += 1; return &token;
}
static void set_type(void *event, uint32_t type) {
    (void)event; (void)type; set_count += 1;
}
static void post(void *event) {
    (void)event; post_count += 1;
}
static void release(void *event) {
    (void)event; release_count += 1;
}

int main(void) {
    bool failed = !MFPostKeyboardEventSafely(59, true, 0, null_create, set_type, post, release);
    if (!failed || created != 1 || set_count != 0 || post_count != 0 || release_count != 0) return 1;

    created = set_count = post_count = release_count = 0;
    bool succeeded = MFPostKeyboardEventSafely(59, true, 0, valid_create, set_type, post, release);
    if (!succeeded || created != 1 || set_count != 1 || post_count != 1 || release_count != 1) return 2;
    puts("ok");
    return 0;
}
'''


class KeyboardEventSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("cc") or shutil.which("clang")
        if compiler is None:
            raise AssertionError("no C compiler is available for the keyboard event safety test")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="mmf-keyboard-safety-test-")
        cls.addClassCleanup(cls.tempdir.cleanup)
        source = Path(cls.tempdir.name) / "harness.c"
        executable = Path(cls.tempdir.name) / "harness"
        source.write_text(HARNESS)
        result = subprocess.run(
            [compiler, "-std=c11", "-I", str(ROOT), str(source), "-o", str(executable)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"keyboard safety harness failed to compile:\n{result.stderr}")
        cls.executable = executable

    def test_null_event_creation_does_not_set_post_or_release(self):
        result = subprocess.run(
            [str(self.executable)], cwd=ROOT, check=False, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_actions_uses_the_production_safety_boundary(self):
        source = ACTIONS.read_text()
        self.assertIn('#import "KeyboardEventSafety.h"', source)
        self.assertIn("MFPostKeyboardEventSafely(", source)
        self.assertTrue(SAFETY_HEADER.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
