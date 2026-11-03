#!/usr/bin/env python3
"""Exercise the production button routing seam without constructing system events."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "Helper/Core/Buttons/ClickCycleReleaseRouter.swift"
DISPATCH = ROOT / "Helper/Core/Buttons/ButtonReleaseDispatch.swift"
CYCLE = ROOT / "Helper/Core/Buttons/ClickCycle.swift"
COOL_TIMER = ROOT / "Shared/Utility/CoolTimer.swift"
BUTTONS = ROOT / "Helper/Core/Buttons/Buttons.swift"


HARNESS = r'''
final class CallbackSink {
    var events: [String] = []
}

struct InputFixture {
    var dispatch = ButtonReleaseDispatch()
    var callbacks = ClickCycleReleaseRouter()
    let callbackSink = CallbackSink()
    var intercepted: [String] = []
    var passedThrough: [String] = []
    var unpairedReleases: [String] = []

    mutating func registerRelease(deviceID: Int64, button: Int, label: String) {
        let sink = callbackSink
        callbacks.append(
            deviceID: deviceID,
            button: button,
            callbacks: [{ sink.events.append(label) }]
        )
    }

    mutating func down(
        deviceID: Int64,
        button: Int,
        activeCycle: Bool,
        computedMaxLevel: Int,
        armReleaseCallback: Bool = false
    ) {
        let route = dispatch.routeDown(
            deviceID: deviceID,
            button: button,
            clickCycleIsActive: activeCycle,
            maxClickLevel: computedMaxLevel
        )
        record(deviceID: deviceID, button: button, phase: "down", passThrough: route.passThrough)
        if armReleaseCallback {
            registerRelease(deviceID: deviceID, button: button, label: "\(deviceID):\(button):release")
        }
    }

    mutating func up(deviceID: Int64, button: Int) {
        let route = dispatch.routeRelease(deviceID: deviceID, button: button)
        _ = callbacks.consume(deviceID: deviceID, button: button)
        if !route.downWasSeen {
            unpairedReleases.append("\(deviceID):\(button)")
        }
        record(deviceID: deviceID, button: button, phase: "up", passThrough: route.passThrough)
    }

    mutating private func record(deviceID: Int64, button: Int, phase: String, passThrough: Bool) {
        let event = "\(deviceID):\(button):\(phase)"
        if passThrough {
            passedThrough.append(event)
        } else {
            intercepted.append(event)
        }
    }
}

@main
struct Main {
    static func main() {
        var interleaved = InputFixture()
        interleaved.down(deviceID: 1, button: 3, activeCycle: false, computedMaxLevel: 2)
        interleaved.up(deviceID: 1, button: 3)
        interleaved.down(deviceID: 1, button: 4, activeCycle: false, computedMaxLevel: 0)
        interleaved.down(deviceID: 1, button: 3, activeCycle: true, computedMaxLevel: 99)
        interleaved.up(deviceID: 1, button: 4)
        interleaved.up(deviceID: 1, button: 3)
        precondition(interleaved.intercepted == [
            "1:3:down", "1:3:up", "1:3:down", "1:3:up"
        ])
        precondition(interleaved.passedThrough == ["1:4:down", "1:4:up"])

        var reversed = InputFixture()
        reversed.down(deviceID: 1, button: 4, activeCycle: false, computedMaxLevel: 0)
        reversed.down(deviceID: 1, button: 3, activeCycle: false, computedMaxLevel: 2)
        reversed.up(deviceID: 1, button: 4)
        reversed.up(deviceID: 1, button: 3)
        precondition(reversed.intercepted == ["1:3:down", "1:3:up"])
        precondition(reversed.passedThrough == ["1:4:down", "1:4:up"])

        var timerAndCallbacks = InputFixture()
        timerAndCallbacks.down(
            deviceID: 1,
            button: 3,
            activeCycle: false,
            computedMaxLevel: 2,
            armReleaseCallback: true
        )
        timerAndCallbacks.down(deviceID: 1, button: 4, activeCycle: false, computedMaxLevel: 0)
        timerAndCallbacks.up(deviceID: 1, button: 4)
        timerAndCallbacks.up(deviceID: 1, button: 3)
        precondition(timerAndCallbacks.callbackSink.events == ["1:3:release"])
        precondition(timerAndCallbacks.passedThrough == ["1:4:down", "1:4:up"])
        precondition(timerAndCallbacks.intercepted == ["1:3:down", "1:3:up"])

        var repeated = InputFixture()
        repeated.down(deviceID: 1, button: 3, activeCycle: false, computedMaxLevel: 2)
        repeated.down(deviceID: 1, button: 3, activeCycle: true, computedMaxLevel: 99)
        repeated.up(deviceID: 1, button: 3)
        repeated.up(deviceID: 1, button: 3)
        repeated.up(deviceID: 1, button: 3)
        precondition(repeated.intercepted == [
            "1:3:down", "1:3:down", "1:3:up", "1:3:up"
        ])
        precondition(repeated.passedThrough == ["1:3:up"])
        precondition(repeated.unpairedReleases == ["1:3"])

        var devices = InputFixture()
        devices.down(
            deviceID: 1,
            button: 3,
            activeCycle: false,
            computedMaxLevel: 2,
            armReleaseCallback: true
        )
        devices.down(deviceID: 2, button: 3, activeCycle: false, computedMaxLevel: 0)
        devices.up(deviceID: 2, button: 3)
        devices.up(deviceID: 1, button: 3)
        precondition(devices.callbackSink.events == ["1:3:release"])
        precondition(devices.passedThrough == ["2:3:down", "2:3:up"])
        precondition(devices.intercepted == ["1:3:down", "1:3:up"])

        var orphanCallback = InputFixture()
        orphanCallback.registerRelease(deviceID: 1, button: 4, label: "orphan")
        orphanCallback.up(deviceID: 1, button: 4)
        precondition(orphanCallback.callbackSink.events == ["orphan"])
        precondition(orphanCallback.passedThrough == ["1:4:up"])
        precondition(orphanCallback.unpairedReleases == ["1:4"])

        print("ok")
    }
}
'''


CONTEXT_HARNESS = r'''
import Cocoa

let kMFEventPassThroughRefusal = 0
let kMFEventPassThroughApproval = 1
typealias MFEventPassThroughEvaluation = Int

struct MFMouseButtonNumber {
    let rawValue: UInt32

    init(_ rawValue: UInt32) {
        self.rawValue = rawValue
    }

    init(rawValue: UInt32) {
        self.rawValue = rawValue
    }
}

enum MFActionPhase: Equatable {
    case start
    case end
    case combined
}

let kMFActionPhaseStart = MFActionPhase.start
let kMFActionPhaseEnd = MFActionPhase.end
let kMFActionPhaseCombined = MFActionPhase.combined

func DDLogDebug(_ message: String) {}
func assertRunLoop(_ runLoop: CFRunLoop) {}

final class GlobalEventTapThread {
    static func runLoop() -> CFRunLoop { CFRunLoopGetCurrent() }
}

final class Device: NSObject {
    let identifier: Int64

    init(_ identifier: Int64) {
        self.identifier = identifier
    }

    func uniqueID() -> NSNumber { NSNumber(value: identifier) }
    func name() -> String { "device-\(identifier)" }
}

final class HelperState {
    static let shared = HelperState()
    func updateActiveDevice(event: CGEvent) {}
}

final class ButtonModifiers: NSObject {
    func update(withButton button: MFMouseButtonNumber, clickLevel: Int, downNotUp mouseDown: Bool) {}
    func killButton(_ button: MFMouseButtonNumber) {}
}

final class TrialCounter {
    static let shared = TrialCounter()
    func handleUse() {}
}

final class ActionSink {
    static var events: [String] = []
}

final class Actions {
    static func executeActionArray(_ actionArray: NSArray, phase: MFActionPhase) {
        guard let label = actionArray.firstObject as? String else { return }
        let suffix: String
        switch phase {
        case .start: suffix = "-start"
        case .end: suffix = "-end"
        case .combined: suffix = "-combined"
        }
        ActionSink.events.append(label + suffix)
    }
}

final class Modifiers {
    static func modifiers(with event: CGEvent) -> NSDictionary { NSDictionary() }
    static func handleModificationHasBeenUsed() {}
}

final class Remap {
    static var remaps: NSDictionary { NSDictionary() }

    static func modifications(withModifiers modifiers: NSDictionary) -> NSDictionary? {
        let shifted = (modifiers.object(forKey: "shift") as? NSNumber)?.boolValue ?? false
        let label = shifted ? "shift" : "default"
        let levelOne = NSMutableDictionary()
        levelOne["click"] = NSArray(object: "\(label)-click")
        levelOne["hold"] = NSArray(object: "\(label)-hold")
        let levelTwo = NSMutableDictionary()
        levelTwo["click"] = NSArray(object: "\(label)-double")
        let buttonThree = NSMutableDictionary()
        buttonThree[NSNumber(value: 1)] = levelOne
        buttonThree[NSNumber(value: 2)] = levelTwo
        let result = NSMutableDictionary()
        result[NSNumber(value: 3)] = buttonThree
        return result
    }
}

final class RemapsAnalyzer {
    private static func levelMap(_ modifications: NSDictionary, button: NSNumber, level: NSNumber) -> NSDictionary? {
        guard let buttonMap = modifications.object(forKey: button) as? NSDictionary else { return nil }
        return buttonMap.object(forKey: level) as? NSDictionary
    }

    static func maxLevel(forButton button: NSNumber, remaps: NSDictionary, modificationsActingOnThisButton modifications: NSDictionary) -> Int {
        guard let buttonMap = modifications.object(forKey: button) as? NSDictionary else { return 0 }
        return buttonMap.allKeys.compactMap { ($0 as? NSNumber)?.intValue }.max() ?? 0
    }

    static func assessMappingLandscape(
        withButton button: NSNumber,
        level: NSNumber,
        modificationsActingOnThisButton modifications: NSDictionary,
        remaps: NSDictionary,
        thisClickDoBe clickExists: inout ObjCBool,
        thisDownDoBe downExists: inout ObjCBool,
        greaterDoBe greaterExists: inout ObjCBool
    ) {
        guard let current = levelMap(modifications, button: button, level: level) else { return }
        clickExists = ObjCBool(current.object(forKey: "click") != nil)
        downExists = ObjCBool(current.object(forKey: "hold") != nil)
        guard let buttonMap = modifications.object(forKey: button) as? NSDictionary else { return }
        greaterExists = ObjCBool(buttonMap.allKeys.contains { key in
            guard let number = key as? NSNumber else { return false }
            guard number.intValue > level.intValue else { return false }
            return (buttonMap.object(forKey: number) as? NSDictionary)?.count ?? 0 > 0
        })
    }
}

final class Math {
    static func intCycle(x: Int, lower: Int, upper: Int) -> Int {
        guard upper >= lower else { return 0 }
        return x > upper ? lower : x
    }
}

@main
struct Main {
    static let device = Device(1)

    static func send(button: Int, down: Bool, modifiers: NSDictionary) {
        _ = Buttons.handleInputForTesting(
            device: device,
            button: NSNumber(value: button),
            downNotUp: down,
            modifiers: modifiers
        )
    }

    static func waitForTimers() {
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.28))
    }

    static func main() {
        let shifted: NSDictionary = ["shift": NSNumber(value: true)]
        let normal: NSDictionary = ["shift": NSNumber(value: false)]

        ActionSink.events.removeAll()
        send(button: 3, down: true, modifiers: normal)
        send(button: 3, down: false, modifiers: normal)
        send(button: 3, down: true, modifiers: normal)
        send(button: 3, down: false, modifiers: normal)
        waitForTimers()
        precondition(ActionSink.events == ["default-double-start", "default-double-end"], "default context: \(ActionSink.events)")

        ActionSink.events.removeAll()
        send(button: 3, down: true, modifiers: shifted)
        send(button: 3, down: false, modifiers: shifted)
        send(button: 4, down: true, modifiers: normal)
        send(button: 4, down: false, modifiers: normal)
        send(button: 3, down: true, modifiers: normal)
        send(button: 3, down: false, modifiers: normal)
        waitForTimers()
        precondition(ActionSink.events == ["shift-double-start", "shift-double-end"], "double-click context: \(ActionSink.events)")

        ActionSink.events.removeAll()
        send(button: 3, down: true, modifiers: shifted)
        send(button: 4, down: true, modifiers: normal)
        send(button: 4, down: false, modifiers: normal)
        waitForTimers()
        send(button: 3, down: false, modifiers: normal)
        precondition(ActionSink.events == ["shift-hold-start", "shift-hold-end"], "hold context: \(ActionSink.events)")

        print("ok")
    }
}
'''


class ButtonReleaseRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("swiftc")
        if compiler is None:
            raise AssertionError("swiftc is required for the release routing test")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="mmf-button-release-test-")
        cls.addClassCleanup(cls.tempdir.cleanup)
        harness = Path(cls.tempdir.name) / "harness.swift"
        executable = Path(cls.tempdir.name) / "harness"
        harness.write_text(HARNESS)
        result = subprocess.run(
            [compiler, str(ROUTER), str(DISPATCH), str(harness), "-o", str(executable)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise AssertionError(f"release routing harness failed to compile:\n{result.stderr}")
        cls.executable = executable

    def test_interleaved_release_and_pass_through_semantics(self):
        result = subprocess.run(
            [str(self.executable)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_buttons_uses_the_production_release_dispatch(self):
        source = BUTTONS.read_text()
        self.assertIn("buttonReleaseDispatch.routeDown", source)
        self.assertIn("buttonReleaseDispatch.routeRelease", source)
        self.assertIn("clickCycle.consumeReleaseCallbacks", source)
        self.assertNotIn("clickCycle.shouldConsumeRelease", source)


class ButtonContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("swiftc")
        if compiler is None:
            raise AssertionError("swiftc is required for the button context test")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="mmf-button-context-test-")
        cls.addClassCleanup(cls.tempdir.cleanup)
        harness = Path(cls.tempdir.name) / "harness.swift"
        executable = Path(cls.tempdir.name) / "harness"
        harness.write_text(CONTEXT_HARNESS)
        result = subprocess.run(
            [
                compiler,
                str(CYCLE),
                str(ROUTER),
                str(DISPATCH),
                str(COOL_TIMER),
                str(BUTTONS),
                str(harness),
                "-o",
                str(executable),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise AssertionError(f"button context harness failed to compile:\n{result.stderr}")
        cls.executable = executable

    def test_unmapped_interleaving_keeps_cycle_context_for_double_click_and_hold(self):
        result = subprocess.run(
            [str(self.executable)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_buttons_uses_a_cycle_context_snapshot(self):
        source = BUTTONS.read_text()
        self.assertIn("ClickCycleContext", source)
        self.assertIn("contextForActiveCycle", source)
        self.assertIn("context: inputContext", source)
        self.assertNotIn("self.modifications", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
