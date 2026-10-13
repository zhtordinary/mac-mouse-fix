# Personal-use maintenance history

## 2026-10-13 — Mac mini Karabiner mouse prerequisite

### Finding

The earlier middle-button tests were not valid proof of WeType compatibility. Karabiner's Devices page showed both Rapoo pointing-device interfaces with `Modify events` off. Only the receiver's keyboard interface was enabled. The live configuration had no per-device enablement.

`karabiner_cli --list-connected-devices` identified:

| Interface | Vendor / product | Device ID |
| --- | --- | --- |
| Rapoo USB receiver keyboard | 9390 / 4104 | 4294970422 |
| Rapoo USB receiver mouse | 9390 / 4104 | 4294970426 |
| Rapoo Bluetooth LE mouse | 14 / 13330 | 4295028643 |

The earlier core-service `grabbed` log was for device `4294970422`, the keyboard interface. EventViewer repeatedly showed an empty raw-event list while the selected interface was the receiver keyboard. No physical middle-button event was established by those captures. Device IDs are observations from this run, not persistent matching identifiers.

The [official device guide](https://karabiner-elements.pqrs.org/docs/manual/configuration/configure-devices/) confirms that mice are disabled by default and must be enabled to remap mouse buttons.

### Change and scope

The user authorized choosing a connection mode for the next test. The chosen path is the USB 2.4G receiver directly connected to the Mac mini.

Local configuration: `~/.config/karabiner/karabiner.json`.

- Enabled only the USB pointing-device interface (`9390 / 4104`, `is_pointing_device: true`, `ignore: false`).
- Replaced the double-click state machine with one device-scoped `button3` → `left_control` diagnostic rule. The button name still requires physical validation.
- Preserved the disabled F6 rule and virtual-keyboard settings.
- Left Bluetooth configuration, MacBook Air, MMF source code, and the deployed app unchanged.
- Stopped EventViewer raw capture before enabling the diagnostic. Raw capture bypasses Karabiner modifications and must not remain active during the voice-input test.

### Validation

- Parsed the JSON and asserted the USB-only device entry, preserved F6 and virtual-keyboard settings, one diagnostic manipulator, and absence of `wetype_middle_double`.
- Extracted the rules into a temporary distribution-format file and ran `karabiner_cli --lint-complex-modifications`: `ok`. The temporary file was removed.
- `/var/log/karabiner/core_service.log` showed automatic configuration reload at `14:50:50`, `virtual_hid_pointing_ready_response: true`, and USB mouse device `4294970426` monitored in `grabbed` mode at `14:50:51`.
- Physical input, WeType voice-UI activation, normal mouse behavior, and coexistence with MMF remain unverified. No claim of a complete fix or permission to deploy this configuration to the Air follows from the checks above.

### Rollback

Pre-change backup on the Mac mini:

`/Users/zibuyu/Downloads/karabiner.json.before-usb-mouse-single-20261013-144911`

To restore that exact test state, stop EventViewer raw capture, then run:

```bash
cp -p "$HOME/Downloads/karabiner.json.before-usb-mouse-single-20261013-144911" \
  "$HOME/.config/karabiner/karabiner.json"
```

Karabiner reloads the configuration automatically. Verify the reload in its core-service log. This backup restores the preceding experimental double-click rule and the default-disabled mouse state; it is not a known-working voice-input configuration.

## 2026-10-14 — WeChat Input (WeType) voice input companion implementation

### Context & Decision
The user required triggering WeChat Input (WeType) voice input via mouse middle double-click while preserving all Mac Mouse Fix single-click actions, smart zoom, gestures, and Universal Control cross-screen mouse roaming between MacBook Air and Mac mini.

1. **Root cause analysis**: WeType's `ShortcutKeyMonitor` validates hardware-level keyboard scan codes; synthetic `CGEvent` keyboard events are silently dropped by design. Capturing mouse events via DriverKit causes 300ms click latency and breaks Universal Control.
2. **Architectural choice**: Keep Mac Mouse Fix's `personal-use` build completely pristine. Implement a standalone companion application `WeTypeVoiceTrigger.app` located under `WeTypeVoiceTrigger/`.
3. **Implementation & Optimization (v2 Turbo)**:
   - Uses `kCGHIDEventTap` in `.listenOnly` mode to passively detect middle double-clicks (0.06s–0.65s threshold, 0.50s cooldown) without consuming or delaying physical mouse events.
   - Non-blocking asynchronous accessibility dispatch triggers `com.apple.TextInputMenuAgent` statusItem expansion, paired with 15ms micro-polling to invoke `语音输入（左 control）`.
   - Measured latency dropped from 1540ms to ~220ms (a 6x speedup).
   - Built on standard `NSApplication` event loop with non-blocking timer for robust TCC authorization handling.
4. **Documentation**:
   - Canonical documentation: `WeTypeVoiceTrigger/README.md`
   - Build & sync script: `WeTypeVoiceTrigger/build.sh`
   - Source code: `WeTypeVoiceTrigger/main.swift`

