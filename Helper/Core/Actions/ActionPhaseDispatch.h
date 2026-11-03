//
// Keyboard action phase dispatch shared by the helper and its isolated test.
//

#ifndef MF_ACTION_PHASE_DISPATCH_H
#define MF_ACTION_PHASE_DISPATCH_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* These values mirror MFActionPhase in Actions.h without requiring Foundation. */
enum MFKeyboardActionPhase {
    MFKeyboardActionPhaseStart = 0,
    MFKeyboardActionPhaseEnd = 1,
    MFKeyboardActionPhaseCombined = 2,
};

typedef enum {
    MFKeyboardActionEventStandaloneDown,
    MFKeyboardActionEventStandaloneUp,
    MFKeyboardActionEventShortcut,
} MFKeyboardActionEventKind;

typedef struct {
    uint16_t keyCode;
    uint64_t modifierFlags;
    bool keyDown;
    MFKeyboardActionEventKind kind;
} MFKeyboardActionEvent;

typedef void (*MFKeyboardActionEventSink)(MFKeyboardActionEvent event);

static inline bool MFIsStandaloneModifierKeyCode(uint16_t keyCode) {
    switch (keyCode) {
        case 0x3B: /* Control */
        case 0x3E: /* Right Control */
        case 0x3A: /* Option */
        case 0x3D: /* Right Option */
        case 0x37: /* Command */
        case 0x36: /* Right Command */
            return true;
        default:
            return false;
    }
}

static inline void MFEmitStandaloneModifierEvent(
    MFKeyboardActionEventSink sink,
    uint16_t keyCode,
    bool keyDown
) {
    sink((MFKeyboardActionEvent){
        .keyCode = keyCode,
        .modifierFlags = 0,
        .keyDown = keyDown,
        .kind = keyDown ? MFKeyboardActionEventStandaloneDown : MFKeyboardActionEventStandaloneUp,
    });
}

/* This is the production phase policy; callers provide only the event sink. */
static inline void MFDispatchKeyboardAction(
    uint16_t keyCode,
    uint64_t modifierFlags,
    int phase,
    MFKeyboardActionEventSink sink
) {
    if (sink == NULL) {
        return;
    }

    bool standaloneModifier = modifierFlags == 0 && MFIsStandaloneModifierKeyCode(keyCode);
    if (phase == MFKeyboardActionPhaseEnd) {
        if (standaloneModifier) {
            MFEmitStandaloneModifierEvent(sink, keyCode, false);
        }
        return;
    }

    if (standaloneModifier) {
        if (phase == MFKeyboardActionPhaseStart) {
            MFEmitStandaloneModifierEvent(sink, keyCode, true);
        } else if (phase == MFKeyboardActionPhaseCombined) {
            MFEmitStandaloneModifierEvent(sink, keyCode, true);
            MFEmitStandaloneModifierEvent(sink, keyCode, false);
        }
        return;
    }

    if (phase == MFKeyboardActionPhaseStart || phase == MFKeyboardActionPhaseCombined) {
        sink((MFKeyboardActionEvent){
            .keyCode = keyCode,
            .modifierFlags = modifierFlags,
            .keyDown = false,
            .kind = MFKeyboardActionEventShortcut,
        });
    }
}

#endif
