//
// --------------------------------------------------------------------------
// KeyCaptureMode.m
// Created for Mac Mouse Fix (https://github.com/noah-nuebling/mac-mouse-fix)
// Created by Noah Nuebling in 2022
// Licensed under the MMF License (https://github.com/noah-nuebling/mac-mouse-fix/blob/master/License)
// --------------------------------------------------------------------------
//

#import "KeyCaptureMode.h"
#import <Cocoa/Cocoa.h>
#import <Carbon/Carbon.h>
#import "ModificationUtility.h"
#import "MFMessagePort.h"
#import "Logging.h"
#import "GlobalEventTapThread.h"
#import "Threads.h"

@implementation KeyCaptureMode


/// Explanation for this class:
///  When the user records keyboard shortcuts in the mainApp we wanted to use eventTaps for that. I think otherwise certain keys weren't captured. Not sure though. The helper already has permissions to use eventTaps so the mainApp delegates the capturing to the helper.


CFMachPortRef _keyCaptureEventTap;
CGKeyCode _pendingStandaloneModifierKeyCode = USHRT_MAX;

static BOOL keyCaptureModeIsStandaloneModifierKeyCode(CGKeyCode keyCode) {
    switch (keyCode) {
        case kVK_Control:
        case kVK_RightControl:
        case kVK_Option:
        case kVK_RightOption:
        case kVK_Command:
        case kVK_RightCommand:
            return YES;
        default:
            return NO;
    }
}

static BOOL keyCaptureModeModifierIsDown(CGKeyCode keyCode, CGEventFlags flags) {
    switch (keyCode) {
        case kVK_Control:
        case kVK_RightControl:
            return (flags & kCGEventFlagMaskControl) != 0;
        case kVK_Option:
        case kVK_RightOption:
            return (flags & kCGEventFlagMaskAlternate) != 0;
        case kVK_Command:
        case kVK_RightCommand:
            return (flags & kCGEventFlagMaskCommand) != 0;
        default:
            return NO;
    }
}

+ (void)enable {
    assertRunLoop(GlobalEventTapThread.runLoop);

    DDLogInfo("Enabling keyCaptureMode");
    
    if (!_keyCaptureEventTap) {
        _keyCaptureEventTap = [
            ModificationUtility
            createEventTapWithLocation: kCGHIDEventTap
            mask: CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventFlagsChanged) | CGEventMaskBit(NSEventTypeSystemDefined)
            option: kCGEventTapOptionDefault
            placement: kCGHeadInsertEventTap
            callback: keyCaptureModeCallback
            runLoop: GlobalEventTapThread.runLoop
        ];
    }
    _pendingStandaloneModifierKeyCode = USHRT_MAX;
    CGEventTapEnable(_keyCaptureEventTap, true);
}

+ (void)disable {
    assertRunLoop(GlobalEventTapThread.runLoop);
    _pendingStandaloneModifierKeyCode = USHRT_MAX;
    CGEventTapEnable(_keyCaptureEventTap, false);
}

CGEventRef _Nullable keyCaptureModeCallback(CGEventTapProxy proxy, CGEventType type, CGEventRef event, void *userInfo) {
    assertRunLoop(GlobalEventTapThread.runLoop);

    CGEventFlags flags  = CGEventGetFlags(event);
    
    NSDictionary *payload;
    
    if (type == kCGEventKeyDown) {
        
        CGKeyCode keyCode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);
        _pendingStandaloneModifierKeyCode = USHRT_MAX;
        
        if (keyCaptureModePayloadIsValidWithKeyCode(keyCode, flags)) {
            
            payload = @{
                @"keyCode": @(keyCode),
                @"flags": @(flags),
            };
            
            [MFMessagePort sendMessage: @"keyCaptureModeFeedback" withPayload: payload waitForReply: NO];
            [KeyCaptureMode disable];
        }

    } else if (type == kCGEventFlagsChanged) {
        
        CGKeyCode keyCode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);
        if (keyCaptureModeIsStandaloneModifierKeyCode(keyCode)) {
            if (keyCaptureModeModifierIsDown(keyCode, flags)) {
                _pendingStandaloneModifierKeyCode = keyCode;
            } else if (_pendingStandaloneModifierKeyCode == keyCode) {
                payload = @{
                    @"keyCode": @(keyCode),
                    @"flags": @(0),
                };
                [MFMessagePort sendMessage: @"keyCaptureModeFeedback" withPayload: payload waitForReply: NO];
                _pendingStandaloneModifierKeyCode = USHRT_MAX;
                [KeyCaptureMode disable];
            }
        }

    } else if (type == NSEventTypeSystemDefined) {
        
        NSEvent *e = [NSEvent eventWithCGEvent:event];
        
        MFSystemDefinedEventType type = (MFSystemDefinedEventType)(e.data1 >> 16);
        
        if (keyCaptureModePayloadIsValidWithEvent(e, flags, type)) {
            
            DDLogDebug("Capturing system event with data1: %ld, data2: %ld", e.data1, e.data2);
            
            payload = @{
                @"systemEventType": @(type),
                @"flags": @(flags),
            };
            
            [MFMessagePort sendMessage: @"keyCaptureModeFeedbackWithSystemEvent" withPayload: payload waitForReply: NO];
            [KeyCaptureMode disable];
        }
        
    }
    
    
    return nil;
}
static bool keyCaptureModePayloadIsValidWithKeyCode(CGKeyCode keyCode, CGEventFlags flags) {
    return true; /// keyCode 0 is 'A'
}

static bool keyCaptureModePayloadIsValidWithEvent(NSEvent *e, CGEventFlags flags, MFSystemDefinedEventType type) {

    BOOL isSub8 = (e.subtype == 8); /// 8 -> Maybe `NX_SUBTYPE_AUX_CONTROL_BUTTONS` says Opus 5.5
    BOOL isKeyDown = (e.data1 & kMFSystemDefinedEventPressedMask) == 0;
    BOOL secondDataIsNil = e.data2 == -1; /// The power key up event has both data fields be 0
    BOOL typeIsBlackListed = type == NX_KEYTYPE_CAPS_LOCK;
    
    BOOL isValid = isSub8 && isKeyDown && secondDataIsNil && !typeIsBlackListed;
    
    if (!isValid) {
        DDLogDebug("KeyCaptureMode received systemDefinedEvent but it is not valid – isSubtype8: %d, isKeyDown: %d, secondDataIsNil: %d, typeIsBlackListed: %d – event: %@, flags: %llu, type: %d", isSub8, isKeyDown, secondDataIsNil, typeIsBlackListed, e, flags, type);
    }
    
    return isValid;
}

@end
