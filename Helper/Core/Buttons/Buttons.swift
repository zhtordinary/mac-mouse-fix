//
// --------------------------------------------------------------------------
// Buttons.swift
// Created for Mac Mouse Fix (https://github.com/noah-nuebling/mac-mouse-fix)
// Created by Noah Nuebling in 2022
// Licensed under the MMF License (https://github.com/noah-nuebling/mac-mouse-fix/blob/master/License)
// --------------------------------------------------------------------------
//

import Cocoa

@objc class Buttons: NSObject {
    
    /// Ivars

    static private var clickCycle = ClickCycle()
    static private var buttonModifiers = ButtonModifiers()
    @objc static var useButtonModifiers = false
    
    /// Keep per-device/button release pairing separate from the active cycle context.
    static private var buttonReleaseDispatch = ButtonReleaseDispatch()
    
    /// Init
    private static var isInitialized = false
    private static func coolInitialize() {
        isInitialized = true
    }
    
    /// Handling input
    
    @objc static func handleInput(device: Device, button: NSNumber, downNotUp mouseDown: Bool, event: CGEvent) -> MFEventPassThroughEvaluation {
        return handleInput(
            device: device,
            button: button,
            downNotUp: mouseDown,
            event: event,
            candidateModifiers: nil
        )
    }

    /// Keeps the production routing path testable without constructing a system CGEvent.
    static func handleInputForTesting(device: Device, button: NSNumber, downNotUp mouseDown: Bool, modifiers: NSDictionary) -> MFEventPassThroughEvaluation {
        return handleInput(
            device: device,
            button: button,
            downNotUp: mouseDown,
            event: nil,
            candidateModifiers: modifiers
        )
    }

    private static func handleInput(device: Device, button: NSNumber, downNotUp mouseDown: Bool, event: CGEvent?, candidateModifiers: NSDictionary?) -> MFEventPassThroughEvaluation {
        assertRunLoop(GlobalEventTapThread.runLoop())

        let passThroughEvaluation = kMFEventPassThroughRefusal
        
            /// Init
        if !isInitialized { coolInitialize() }
        
        /// Get remaps
        /// Accessing the dict like this is super slow. Casting to NSDictionary and using NSDictionary API to access it's values might fix that. See https://stackoverflow.com/questions/57555444/accessing-object-c-nsdictionary-values-in-swift-is-slow
        let remaps = Remap.remaps
        
        /// Update stuff when clickCycle starts
        
        let buttonNumber = ButtonNumber(truncating: button)
        let deviceID = device.uniqueID().int64Value
        let clickCycleIsActive = clickCycle.isActiveFor(device: device.uniqueID(), button: button)
        let inputContext: ClickCycleContext
        if let activeContext = clickCycle.contextForActiveCycle(device: device.uniqueID(), button: button) {
            inputContext = activeContext
        } else if mouseDown {
            let resolvedModifiers = candidateModifiers
                ?? event.map { Modifiers.modifiers(with: $0) }
                ?? NSDictionary()
            inputContext = ClickCycleContext(
                modifiers: resolvedModifiers,
                modifications: Remap.modifications(withModifiers: resolvedModifiers) ?? NSDictionary()
            )
        } else {
            inputContext = ClickCycleContext(modifiers: NSDictionary(), modifications: NSDictionary())
        }
        var maxClickLevel = 0
        if mouseDown && !clickCycleIsActive {
            
            /// Update active device
            if let event = event {
                HelperState.shared.updateActiveDevice(event: event)
            }
            
            /// Get max clickLevel for this candidate. It becomes active only if ClickCycle accepts this input.
            maxClickLevel = RemapsAnalyzer.maxLevel(forButton: button, remaps: remaps, modificationsActingOnThisButton: inputContext.modifications)
        }
        
        /// Build the callback before the pass-through decision so a registered release can always be consumed.
        let triggerCallback: ClickCycleTriggerCallback = { triggerPhase, clickLevel, device, buttonNumber, onRelease in
            ///
            /// Update modifiers
            ///
            
            if useButtonModifiers {
                
                if triggerPhase == .press {
                    self.buttonModifiers.update(withButton: MFMouseButtonNumber(button.uint32Value), clickLevel: clickLevel, downNotUp: true)
                    onRelease.append {
                        self.buttonModifiers.update(withButton: MFMouseButtonNumber(button.uint32Value), clickLevel: clickLevel, downNotUp: false)
                    }
                }
            }
            
            ///
            /// Send triggers
            ///
            
            /// Debug
            DDLogDebug("triggerCallback - lvl: \(clickLevel), phase: \(triggerPhase), btn: \(buttonNumber), dev: \"\(device.name())\"")
            
            /// Asses 'mappingLandscape'
            ///     In theory we only have to do this on mouse down, because on mouse up the clickLevel doesn't change, and so no params for `assessMappingLandscape()` change
            
            var clickActionOfThisLevelExists: ObjCBool = false
            var effectForMouseDownStateOfThisLevelExists: ObjCBool = false
            var effectOfGreaterLevelExists: ObjCBool = false
            
            RemapsAnalyzer.assessMappingLandscape(withButton: button as NSNumber, level: clickLevel as NSNumber, modificationsActingOnThisButton: inputContext.modifications, remaps: remaps, thisClickDoBe: &clickActionOfThisLevelExists, thisDownDoBe: &effectForMouseDownStateOfThisLevelExists, greaterDoBe: &effectOfGreaterLevelExists)
            
            /// Create trigger -> action map based on mappingLandscape
            
            var map: [ClickCycleTriggerPhase: (String, MFActionPhase)] = Dictionary(minimumCapacity: 3)
            
            /// Map for click actions
            if clickActionOfThisLevelExists.boolValue {
                if effectOfGreaterLevelExists.boolValue {
                    map[.levelExpired]          = ("click", kMFActionPhaseCombined)
                } else if effectForMouseDownStateOfThisLevelExists.boolValue {
                    map[.release]               = ("click", kMFActionPhaseCombined)
                    //map[.releaseFromHold]       = ("click", kMFActionPhaseCombined)
                } else {
                    map[.press]                 = ("click", kMFActionPhaseStart)
                }
            }
            
            /// Map for hold actions
            if effectForMouseDownStateOfThisLevelExists.boolValue {
                map[.hold]                  = ("hold", kMFActionPhaseStart)
            }
            
            /// Get action for current trigger
            ///     This code is horrible to write in Swift. Deal with remapsDict in Objc whenever possible

            /// Get actionArray
            guard
                let (duration, startOrEnd) = map[triggerPhase],
                //let m1 = modifications[button] as? [AnyHashable: Any],
                let m1 = inputContext.modifications.object(forKey: button) as? NSDictionary,
                //let m2 = m1[clickLevel as NSNumber] as? [AnyHashable: Any],
                let m2 = m1.object(forKey: clickLevel) as? NSDictionary,
                //let m3 = m2[duration],
                let actionArray = m2.object(forKey: duration) as? NSArray /// Not nil -> a click/hold action does exist for this button + level + duration
                //let actionArray = m3 as? [[AnyHashable: Any]]
            else {
                return /// Return if there's no action array to send
            }
            
            /// Add modifiers to actionArray for addMode. See Remap -> addMode for context
            ///     Edit: We don't need this anymore now that we're using the addModeSwizzler
            //if actionArray[0][kMFActionDictKeyType] as! String == kMFActionDictTypeAddModeFeedback {
            //    actionArray[0][kMFRemapsKeyModificationPrecondition] = inputContext.modifiers
            //}

            /// Notify TrialCounter.swift
            TrialCounter.shared.handleUse()
            
            /// Execute actionArray
            if startOrEnd == kMFActionPhaseCombined {
                Actions.executeActionArray(actionArray, phase: kMFActionPhaseCombined)
            } else if startOrEnd == kMFActionPhaseStart {
                Actions.executeActionArray(actionArray, phase: kMFActionPhaseStart)
                onRelease.append {
                    DDLogDebug("triggerCallback - unconditionalRelease button \(button)")
                    Actions.executeActionArray(actionArray, phase: kMFActionPhaseEnd)
                }
            }
            
            /// Notify triggering button
            ///     For levelExpired and .releaseFromHold, we know that the clickCycle will be killed right after this callback.
            ///     In that case it might not be necessary to notify the triggering button.
            ///     Edit: We also want to kill the triggering button as a modifier though
            self.handleButtonHasHadDirectEffect_Unsafe(device: device, button: button)
            
            /// Notify modifiers
            ///     (Probably unnecessary, because the only modifiers that can be "deactivated" are buttons. And since there's only one clickCycle, any buttons modifying the current one should already be zombified)
            ///
            Modifiers.handleModificationHasBeenUsed()
        }

        let releaseDispatch: ButtonReleaseDispatchResult
        if mouseDown {
            releaseDispatch = buttonReleaseDispatch.routeDown(
                deviceID: deviceID,
                button: buttonNumber,
                clickCycleIsActive: clickCycleIsActive,
                maxClickLevel: maxClickLevel
            )
        } else {
            releaseDispatch = buttonReleaseDispatch.routeRelease(
                deviceID: deviceID,
                button: buttonNumber
            )
            _ = clickCycle.consumeReleaseCallbacks(device: device, button: buttonNumber)
        }

        if releaseDispatch.passThrough {
            return kMFEventPassThroughApproval
        }

        clickCycle.handleClick(
            device: device,
            button: buttonNumber,
            downNotUp: mouseDown,
            maxClickLevel: releaseDispatch.maxClickLevel,
            context: inputContext,
            triggerCallback: triggerCallback
        )

        return passThroughEvaluation
    }
    
    
    /// Effect feedback
    
    private static func handleButtonHasHadDirectEffect_Unsafe(device: Device, button: NSNumber) {
        /// Validate
        /// Might wanna `assert(clickCycleIsActive)`
        assert(isInitialized)

        /// Do stuff
        if self.clickCycle.isActiveFor(device: device.uniqueID(), button: button) {
            self.clickCycle.kill()
        }
        if useButtonModifiers {
            self.buttonModifiers.killButton(MFMouseButtonNumber(rawValue: button.uint32Value)) /// Not sure abt this
        }
    }
    
    @objc static func handleButtonHasHadEffectAsModifier(button: NSNumber) {

        assertRunLoop(GlobalEventTapThread.runLoop())

        /// Validate
        /// Might wanna `assert(buttonIsHeld)`
        assert(isInitialized)
        /// Do stuff
        if self.clickCycle.isActiveFor(button: button) {
            self.clickCycle.kill()
        }
    }
    
    /// Interface for accessing submodules
    
    //@objc static func getActiveButtonModifiers_Unsafe(device: Device) -> [[String: Int]] {
    //    return modifierManager.getActiveButtonModifiersForDevice(device: device)
    //}

}
