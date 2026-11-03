//
// Release/pass-through ordering for button input.
//

struct ButtonReleaseDispatchResult {
    let downWasSeen: Bool
    let maxClickLevel: Int
    let passThrough: Bool
}

struct ButtonReleaseDispatch {
    private struct Key: Hashable {
        let deviceID: Int64
        let button: Int
    }

    private struct DownState {
        let maxClickLevel: Int
        let passThrough: Bool
    }

    private var activeMaxClickLevels: [Key: Int] = [:]
    private var pendingDowns: [Key: [DownState]] = [:]

    mutating func routeDown(
        deviceID: Int64,
        button: Int,
        clickCycleIsActive: Bool,
        maxClickLevel: Int
    ) -> ButtonReleaseDispatchResult {
        let key = Key(deviceID: deviceID, button: button)
        let resolvedMaxClickLevel = clickCycleIsActive
            ? (activeMaxClickLevels[key] ?? maxClickLevel)
            : maxClickLevel
        activeMaxClickLevels[key] = resolvedMaxClickLevel
        pendingDowns[key, default: []].append(
            DownState(
                maxClickLevel: resolvedMaxClickLevel,
                passThrough: resolvedMaxClickLevel == 0
            )
        )
        return ButtonReleaseDispatchResult(
            downWasSeen: true,
            maxClickLevel: resolvedMaxClickLevel,
            passThrough: resolvedMaxClickLevel == 0
        )
    }

    mutating func routeRelease(deviceID: Int64, button: Int) -> ButtonReleaseDispatchResult {
        let key = Key(deviceID: deviceID, button: button)
        guard var downs = pendingDowns[key], !downs.isEmpty else {
            return ButtonReleaseDispatchResult(
                downWasSeen: false,
                maxClickLevel: 0,
                passThrough: true
            )
        }

        let down = downs.removeFirst()
        if downs.isEmpty {
            pendingDowns.removeValue(forKey: key)
        } else {
            pendingDowns[key] = downs
        }
        return ButtonReleaseDispatchResult(
            downWasSeen: true,
            maxClickLevel: down.maxClickLevel,
            passThrough: down.passThrough
        )
    }
}
