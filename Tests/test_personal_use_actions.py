#!/usr/bin/env python3
"""Execute the production keyboard phase dispatcher with a recording sink.

The sink records production descriptors and never calls CGEventCreateKeyboardEvent
or CGEventPost; this is an isolated phase/descriptor test, not device validation.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ROOT / "Helper/Core/Actions/Actions.m"
DISPATCH_HEADER = ROOT / "Helper/Core/Actions/ActionPhaseDispatch.h"


HARNESS = r'''
#include "Helper/Core/Actions/ActionPhaseDispatch.h"
#include <stdio.h>
#include <stdlib.h>

static void record(MFKeyboardActionEvent event) {
    printf("%d %u %llu %d\n",
           event.kind,
           event.keyCode,
           (unsigned long long)event.modifierFlags,
           event.keyDown);
}

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    uint16_t keyCode = (uint16_t)strtoul(argv[1], NULL, 0);
    uint64_t flags = (uint64_t)strtoull(argv[2], NULL, 0);
    int phase = (int)strtol(argv[3], NULL, 0);
    MFDispatchKeyboardAction(keyCode, flags, phase, record);
    return 0;
}
'''


class PersonalUseActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = shutil.which("cc") or shutil.which("clang")
        if cls.compiler is None:
            raise AssertionError("no C compiler is available for the production dispatcher test")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="mmf-actions-test-")
        cls.addClassCleanup(cls.tempdir.cleanup)
        source = Path(cls.tempdir.name) / "harness.c"
        cls.executable = Path(cls.tempdir.name) / "harness"
        source.write_text(HARNESS)
        result = subprocess.run(
            [cls.compiler, "-std=c11", "-I", str(ROOT), str(source), "-o", str(cls.executable)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"production dispatcher harness failed to compile:\n{result.stderr}")

    def events(self, key_code, flags, phase):
        result = subprocess.run(
            [str(self.executable), hex(key_code), hex(flags), str(phase)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        events = []
        for line in result.stdout.splitlines():
            kind, key, event_flags, key_down = line.split()
            events.append((int(kind), int(key), int(event_flags), int(key_down)))
        return events

    def test_modifiers_execute_start_end_and_combined_production_phases(self):
        for key_code in (0x3B, 0x3A, 0x37):  # Control, Option, Command
            with self.subTest(key_code=hex(key_code)):
                self.assertEqual(self.events(key_code, 0, 0), [(0, key_code, 0, 1)])
                self.assertEqual(self.events(key_code, 0, 1), [(1, key_code, 0, 0)])
                self.assertEqual(
                    self.events(key_code, 0, 2),
                    [(0, key_code, 0, 1), (1, key_code, 0, 0)],
                )
                self.assertEqual(self.events(key_code, 0, -1), [])
                self.assertEqual(self.events(key_code, 0, 3), [])

    def test_ordinary_shortcuts_keep_one_shot_and_release_safety(self):
        key_code, flags = 0x00, 0x100
        expected = [(2, key_code, flags, 0)]
        self.assertEqual(self.events(key_code, flags, 0), expected)
        self.assertEqual(self.events(key_code, flags, 1), [])
        self.assertEqual(self.events(key_code, flags, 2), expected)

    def test_actions_m_uses_the_same_production_dispatcher(self):
        source = ACTIONS.read_text()
        self.assertIn('#import "ActionPhaseDispatch.h"', source)
        self.assertIn("MFDispatchKeyboardAction(", source)
        self.assertIn("_Static_assert(kMFActionPhaseStart == MFKeyboardActionPhaseStart", source)
        self.assertTrue(DISPATCH_HEADER.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
