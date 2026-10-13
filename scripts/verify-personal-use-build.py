#!/usr/bin/env python3
"""Check the source contract for the personal-use build."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, text: str) -> None:
    content = (ROOT / path).read_text()
    if text not in content:
        raise SystemExit(f"missing expected text in {path}: {text!r}")


def forbid(path: str, text: str) -> None:
    content = (ROOT / path).read_text()
    if text in content:
        raise SystemExit(f"forbidden active UI text remains in {path}: {text!r}")


project = "Mouse Fix.xcodeproj/project.pbxproj"
require(project, 'SWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG PERSONAL_USE";')
require(project, 'SWIFT_ACTIVE_COMPILATION_CONDITIONS = "NDEBUG PERSONAL_USE";')

storyboard = "App/UI/Main/Base.lproj/Main.storyboard"
for menu_title in ("title=\"Activate License...\"", "title=\"Buy Mac Mouse Fix...\""):
    forbid(storyboard, menu_title)

require(
    "Shared/License/Retrieve/GetLicenseState.swift",
    "private static let personalUseLicenseState = MFLicenseState(\n        isLicensed: true,",
)
require(
    "Shared/License/Retrieve/GetLicenseConfig.swift",
    "let result = licenseConfigFallback()",
)
require(
    "Shared/License/Retrieve/GetTrialState.swift",
    "trialIsActive: false",
)
require("Shared/License/License.swift", "@objc static var personalUseBuild: Bool")
require("Shared/License/License.swift", "#if PERSONAL_USE\n        return\n#else")
require("Shared/License/TrialCounter.swift", "#if PERSONAL_USE\n        return\n#endif")
require("App/AppDelegate.m", "if ([License personalUseBuild]) { return; }")
require(
    "App/UI/LicenseSheet/LicenseSheetController.swift",
    "if License.personalUseBuild { return }",
)
require(
    "Helper/UI/TrialNotifications/TrialNotificationController.swift",
    "if License.personalUseBuild { return }",
)
require("Helper/Utility/KeyCaptureMode.m", "kCGEventFlagsChanged")
require("Helper/Utility/KeyCaptureMode.m", "_pendingStandaloneModifierKeyCode")
require("Helper/Core/Actions/Actions.m", "postStandaloneModifierKey")
require("Helper/Core/Actions/Actions.m", "phase == kMFActionPhaseStart")
require("App/UI/Utility/UIStrings/UIStrings.m", "case kVK_Control:")
require(
    "App/UI/Main/Tabs/ButtonTab/RemapTable/RemapTableController.h",
    "- (void)writeDataModelToConfig;",
)
require(
    "App/UI/Main/Tabs/ButtonTab/RemapTable/RemapTableTranslator.m",
    "[self.controller writeDataModelToConfig];",
)

print("personal-use build contract passed")
