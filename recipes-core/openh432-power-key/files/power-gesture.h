/* SPDX-License-Identifier: MIT */
#ifndef POWER_GESTURE_H
#define POWER_GESTURE_H
#include <stdbool.h>
#include <stdint.h>

enum power_action { POWER_NONE, POWER_SUSPEND, POWER_OFF };
struct gesture {
    uint64_t start;
    unsigned step;
    bool active, committed, tone;
};
static inline void gesture_cancel(struct gesture *g)
{
    *g = (struct gesture){0};
}
static inline void gesture_press(struct gesture *g, uint64_t now)
{
    if (!g->active)
        *g = (struct gesture){ .start = now, .active = true };
}
static inline enum power_action gesture_release(struct gesture *g, uint64_t now)
{
    if (!g->active || g->committed)
        return POWER_NONE;
    bool tap = now >= g->start && now - g->start < 1000;
    gesture_cancel(g);
    return tap ? POWER_SUSPEND : POWER_NONE;
}
/* Absolute monotonic deadlines: never compress missed cues into a burst.
 * A scheduling stall cancels, rather than silently advancing to shutdown.
 */
static inline enum power_action gesture_tick(struct gesture *g, uint64_t now)
{
    static const unsigned deadline[] = {1000, 1100, 2000, 2100, 3000, 3100, 4000, 5000};
    if (!g->active || now < g->start)
        return POWER_NONE;
    uint64_t elapsed = now - g->start;
    if (elapsed < deadline[g->step])
        return POWER_NONE;
    if (elapsed - deadline[g->step] > 250) {
        gesture_cancel(g);
        return POWER_NONE;
    }
    g->tone = !(g->step & 1);
    if (g->step == 6)
        g->committed = true;
    if (++g->step == 8) {
        gesture_cancel(g);
        return POWER_OFF;
    }
    return POWER_NONE;
}
#endif
