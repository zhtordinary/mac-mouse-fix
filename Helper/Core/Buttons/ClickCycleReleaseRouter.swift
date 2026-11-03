//
// Release callback ownership for ClickCycle.
//

struct ClickCycleReleaseRouter {
    private struct Key: Hashable {
        let deviceID: Int64
        let button: Int
    }

    private var callbacks: [Key: [() -> Void]] = [:]

    var isEmpty: Bool { callbacks.isEmpty }

    mutating func append(deviceID: Int64, button: Int, callbacks newCallbacks: [() -> Void]) {
        guard !newCallbacks.isEmpty else { return }
        callbacks[Key(deviceID: deviceID, button: button), default: []].append(contentsOf: newCallbacks)
    }

    func contains(deviceID: Int64, button: Int) -> Bool {
        callbacks[Key(deviceID: deviceID, button: button)] != nil
    }

    mutating func consume(deviceID: Int64, button: Int) -> Bool {
        guard let callbacksForRelease = callbacks.removeValue(forKey: Key(deviceID: deviceID, button: button)) else {
            return false
        }
        callbacksForRelease.forEach { $0() }
        return true
    }
}
