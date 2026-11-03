//
// Null-safe keyboard event construction boundary.
//

#ifndef MF_KEYBOARD_EVENT_SAFETY_H
#define MF_KEYBOARD_EVENT_SAFETY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// The production adapter supplies CoreGraphics operations; tests supply inert fakes.
typedef void *(*MFKeyboardEventCreateFunction)(uint16_t keyCode, bool keyDown);
typedef void (*MFKeyboardEventSetTypeFunction)(void *event, uint32_t keyboardType);
typedef void (*MFKeyboardEventPostFunction)(void *event);
typedef void (*MFKeyboardEventReleaseFunction)(void *event);

static inline bool MFPostKeyboardEventSafely(
    uint16_t keyCode,
    bool keyDown,
    uint32_t keyboardType,
    MFKeyboardEventCreateFunction create,
    MFKeyboardEventSetTypeFunction setType,
    MFKeyboardEventPostFunction post,
    MFKeyboardEventReleaseFunction release
) {
    if (create == NULL || setType == NULL || post == NULL || release == NULL) {
        return false;
    }

    void *event = create(keyCode, keyDown);
    if (event == NULL) {
        return false;
    }

    setType(event, keyboardType);
    post(event);
    release(event);
    return true;
}

#endif
