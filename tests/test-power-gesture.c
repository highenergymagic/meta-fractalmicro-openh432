// SPDX-License-Identifier: MIT
#include <assert.h>
#include "power-gesture.h"
int main(void)
{
    struct gesture g = {0};
    assert(gesture_release(&g, 1) == POWER_NONE);
    gesture_press(&g, 100);
    assert(gesture_release(&g, 1099) == POWER_SUSPEND);
    assert(!g.active && !g.tone);
    for (unsigned release = 1000; release < 4000; release += 10) {
        gesture_press(&g, 0);
        for (unsigned t = 0; t < release; t += 10)
            assert(gesture_tick(&g, t) == POWER_NONE);
        assert(gesture_release(&g, release) == POWER_NONE);
        assert(!g.active && !g.tone);
        assert(gesture_tick(&g, 6000) == POWER_NONE);
    }
    gesture_press(&g, 0);
    for (unsigned t = 0; t <= 5000; t += 10) {
        enum power_action a = gesture_tick(&g, t);
        assert(a == (t == 5000 ? POWER_OFF : POWER_NONE));
        bool expected = (t >= 1000 && t < 1100) ||
                        (t >= 2000 && t < 2100) ||
                        (t >= 3000 && t < 3100) ||
                        (t >= 4000 && t < 5000);
        assert(g.tone == expected);
        if (t == 4100) assert(gesture_release(&g, t) == POWER_NONE);
    }
    assert(!g.active && !g.tone);
    gesture_press(&g, 0);
    assert(gesture_tick(&g, 4000) == POWER_NONE);
    assert(!g.active); /* Missed warning cues never silently power off. */
    gesture_press(&g, 5000);
    gesture_press(&g, 5500); /* Repeat cannot restart the deadline. */
    assert(g.start == 5000);
    gesture_cancel(&g); /* Sleep/overflow/restart cancels the gesture. */
    assert(gesture_tick(&g, 10000) == POWER_NONE);
    return 0;
}
