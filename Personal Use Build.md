# Personal-use build

This fork builds Mac Mouse Fix in personal-use mode.

The Xcode project defines `PERSONAL_USE` for the Debug and Release configurations. In this mode:

- The app uses a local licensed state.
- The app does not validate a license key or contact the Gumroad license API.
- The trial counter does not record use or expire.
- The helper does not lock down when a trial ends.
- The trial notification and license sheet do not open.
- The About menu does not show purchase or activation items.
- Keyboard shortcut capture accepts standalone Control, Option, and Command keys.
- Standalone modifier actions save with `flags` set to `0`. A click sends a key-down event and a key-up event. A hold sends key-down on press and key-up on release.

## Build

1. Open `Mouse Fix.xcodeproj` in Xcode.
2. Select the `App` scheme.
3. Build the Debug or Release configuration.

The repository needs a full Xcode installation. Command Line Tools alone cannot build the macOS app target.

Run the source contract check with `python3 scripts/verify-personal-use-build.py`.

## WeType voice-input validation

Standalone modifier output from this app uses software keyboard events. WeType voice-input compatibility must be tested separately; shortcut capture and persistence do not prove that WeType accepts the output.

The external virtual-HID diagnostic is limited to the Mac mini with Karabiner-Elements. Use the Rapoo USB 2.4G receiver directly connected to that Mac. Enable only its pointing-device interface in Karabiner's Devices tab (`vendor_id: 9390`, `product_id: 4104`, `is_pointing_device: true`). Karabiner disables mouse modification by default.

The current diagnostic maps `pointing_button: button3` to `left_control` without a double-click condition. Physical-button identity and WeType activation are pending runtime validation. This is a diagnostic configuration, not virtual-HID integration in Mac Mouse Fix. Verify normal mouse behavior and coexistence with Mac Mouse Fix before adopting it.

Test with a focused editable field and WeType selected as the input method. Tap and release the physical middle button once; verify that the voice-input UI opens. A successful Karabiner rule lint or a ready virtual device is not an activation test. Keep the MacBook Air unchanged until this test passes.

See [Personal Use Maintenance.md](Personal%20Use%20Maintenance.md) for diagnostic evidence and rollback details.

## Source and license

The source keeps the attribution and terms in `License`. Use this fork for personal use. Do not publish a binary without checking the repository license and the licenses of the included dependencies.
