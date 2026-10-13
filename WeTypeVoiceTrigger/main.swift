import Cocoa

func logDebug(_ msg: String) {
    let logPath = "/tmp/wetype_trigger.log"
    let line = "\(Date()): \(msg)\n"
    if !FileManager.default.fileExists(atPath: logPath) {
        FileManager.default.createFile(atPath: logPath, contents: nil, attributes: nil)
    }
    if let handle = FileHandle(forWritingAtPath: logPath) {
        handle.seekToEndOfFile()
        if let data = line.data(using: .utf8) {
            handle.write(data)
        }
        try? handle.close()
    }
}

final class WeTypeVoiceTrigger: NSObject {
    private var lastClickTime: TimeInterval = 0
    private var lastClickLocation: CGPoint?
    private var isCoolingDown = false
    private let cooldownInterval: TimeInterval = 0.50
    private let doubleClickThreshold: TimeInterval = 0.35
    
    private var checkTimer: Timer?
    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?

    func start() {
        logDebug("WeTypeVoiceTrigger daemon started.")
        
        if AXIsProcessTrusted() {
            setupEventTap()
        } else {
            logDebug("Not trusted yet, prompting ONCE...")
            let options: NSDictionary = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
            AXIsProcessTrustedWithOptions(options)
            
            // Non-blocking timer on RunLoop
            checkTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] timer in
                if AXIsProcessTrusted() {
                    logDebug("Accessibility permission GRANTED!")
                    timer.invalidate()
                    self?.checkTimer = nil
                    self?.setupEventTap()
                }
            }
        }
    }
    
    private func setupEventTap() {
        guard eventTap == nil else { return }
        logDebug("Setting up event tap...")
        let mask = (1 << CGEventType.otherMouseDown.rawValue)
        guard let tap = CGEvent.tapCreate(
            tap: .cghidEventTap,
            place: .headInsertEventTap,
            options: .listenOnly,
            eventsOfInterest: CGEventMask(mask),
            callback: { (_, _, event, userInfo) -> Unmanaged<CGEvent>? in
                guard let userInfo = userInfo else { return Unmanaged.passUnretained(event) }
                let trigger = Unmanaged<WeTypeVoiceTrigger>.fromOpaque(userInfo).takeUnretainedValue()
                trigger.handleMouseEvent(event)
                return Unmanaged.passUnretained(event)
            },
            userInfo: Unmanaged.passUnretained(self).toOpaque()
        ) else {
            logDebug("Error: Failed to create event tap")
            return
        }
        
        self.eventTap = tap
        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        self.runLoopSource = source
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
        logDebug(">>> READY! Event tap listening for middle double-clicks!")
    }
    
    private func handleMouseEvent(_ event: CGEvent) {
        let button = event.getIntegerValueField(.mouseEventButtonNumber)
        guard button == 2 else { return }
        
        let now = Date().timeIntervalSince1970
        let loc = event.location
        if isCoolingDown { return }
        
        let diff = now - lastClickTime
        var isWithinDistance = false
        if let lastLoc = lastClickLocation {
            let dx = loc.x - lastLoc.x
            let dy = loc.y - lastLoc.y
            let dist = sqrt(dx * dx + dy * dy)
            isWithinDistance = (dist <= 10.0)
        }
        
        if diff >= 0.06 && diff <= doubleClickThreshold && isWithinDistance {
            lastClickTime = 0
            lastClickLocation = nil
            isCoolingDown = true
            logDebug(">>> Middle double-click detected (diff=\(String(format: "%.3f", diff))s)! Triggering voice input...")
            DispatchQueue.global(qos: .userInteractive).async { [weak self] in
                self?.triggerVoiceInput()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + cooldownInterval) { [weak self] in
                self?.isCoolingDown = false
            }
        } else {
            lastClickTime = now
            lastClickLocation = loc
            logDebug("Middle single-click registered at (\(loc.x), \(loc.y))")
        }
    }
    
    func triggerVoiceInput(completion: (() -> Void)? = nil) {
        guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.TextInputMenuAgent").first else {
            logDebug("Error: TextInputMenuAgent not found")
            return
        }
        let appEl = AXUIElementCreateApplication(app.processIdentifier)
        
        var childrenVal: AnyObject?
        guard AXUIElementCopyAttributeValue(appEl, kAXChildrenAttribute as CFString, &childrenVal) == .success,
              let mbs = childrenVal as? [AXUIElement], mbs.count > 1 else {
            logDebug("Error: mbs traversal failed")
            return
        }
        
        var itemsVal: AnyObject?
        guard AXUIElementCopyAttributeValue(mbs[1], kAXChildrenAttribute as CFString, &itemsVal) == .success,
              let items = itemsVal as? [AXUIElement], let statusItem = items.first else {
            logDebug("Error: statusItem not found")
            return
        }
        
        let t0 = CFAbsoluteTimeGetCurrent()
        DispatchQueue.global(qos: .userInteractive).async {
            AXUIElementPerformAction(statusItem, kAXPressAction as CFString)
        }
        
        for attempt in 0..<40 {
            usleep(15000) // 15ms
            var menuVal: AnyObject?
            if AXUIElementCopyAttributeValue(statusItem, kAXChildrenAttribute as CFString, &menuVal) == .success,
               let menus = menuVal as? [AXUIElement], let menu = menus.first {
                var miVal: AnyObject?
                if AXUIElementCopyAttributeValue(menu, kAXChildrenAttribute as CFString, &miVal) == .success,
                   let mis = miVal as? [AXUIElement], !mis.isEmpty {
                    for mi in mis {
                        var titleVal: AnyObject?
                        AXUIElementCopyAttributeValue(mi, kAXTitleAttribute as CFString, &titleVal)
                        let title = titleVal as? String ?? ""
                        if title.contains("语音输入") {
                            let tHit = CFAbsoluteTimeGetCurrent()
                            AXUIElementPerformAction(mi, kAXPressAction as CFString)
                            logDebug(">>> SUCCESS! Voice input triggered in \(String(format: "%.2f", (tHit - t0) * 1000))ms (attempt \(attempt))")
                            completion?()
                            return
                        }
                    }
                }
            }
        }
        logDebug("Warning: Poll timed out without finding 语音输入")
        completion?()
    }
}

let args = CommandLine.arguments
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let trigger = WeTypeVoiceTrigger()

if args.contains("--daemon") {
    trigger.start()
    app.run()
} else {
    // One-shot mode: trigger voice input once and exit
    trigger.triggerVoiceInput {
        exit(0)
    }
    // Safety timeout in case run loop needed
    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
        exit(0)
    }
    app.run()
}
