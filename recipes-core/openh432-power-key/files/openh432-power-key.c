// SPDX-License-Identifier: MIT
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <systemd/sd-bus.h>
#include "power-gesture.h"

static struct gesture gesture;
static volatile sig_atomic_t stopping;
static uint64_t ignore_until;
static bool sleeping, blocked, tone;
static int beep_fd = -1;
static uint64_t now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0)
        return 0;
    return (uint64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int set_tone(bool on)
{
    if (tone == on)
        return 0;
    struct input_event ev = { .type = EV_SND, .code = SND_BELL, .value = on };
    ssize_t n;
    do n = write(beep_fd, &ev, sizeof(ev)); while (n < 0 && errno == EINTR);
    if (n != (ssize_t)sizeof(ev))
        return n < 0 ? -errno : -EIO;
    tone = on;
    return 0;
}
static void stop_signal(int sig) { (void)sig; stopping = 1; }
static int prepare_sleep(sd_bus_message *m, void *unused, sd_bus_error *error)
{
    int value, r;
    (void)unused; (void)error;
    r = sd_bus_message_read(m, "b", &value);
    if (r < 0) return r;
    sleeping = value;
    gesture_cancel(&gesture);
    blocked = true;
    ignore_until = now_ms() + 2000;
    return set_tone(false);
}
static int action_reply(sd_bus_message *m, void *unused, sd_bus_error *error)
{
    (void)unused; (void)error;
    const sd_bus_error *e = sd_bus_message_get_error(m);
    if (e) fprintf(stderr, "Power action rejected: %s\n", e->message);
    return 0;
}
static int request_action(sd_bus *bus, enum power_action action)
{
    if (stopping || action == POWER_NONE) return 0;
    gesture_cancel(&gesture);
    blocked = true;
    ignore_until = now_ms() + 2000;
    int r = set_tone(false);
    if (r < 0) return r;
    const char *method = action == POWER_OFF ? "PowerOff" : "Suspend";
    fprintf(stderr, "Requesting %s\n", method);
    return sd_bus_call_method_async(bus, NULL, "org.freedesktop.login1",
        "/org/freedesktop/login1", "org.freedesktop.login1.Manager", method,
        action_reply, NULL, "b", 0);
}
static int key_down(int fd)
{
    unsigned char bits[(KEY_MAX + 8) / 8] = {0};
    if (ioctl(fd, EVIOCGKEY(sizeof(bits)), bits) < 0) return -errno;
    return !!(bits[KEY_POWER / 8] & (1U << (KEY_POWER % 8)));
}
int main(void)
{
    sd_bus *bus = NULL;
    sd_bus_message *reply = NULL;
    int key_fd = -1, inhibitor = -1, r = 0, clock = CLOCK_MONOTONIC;
    struct sigaction sa = { .sa_handler = stop_signal };
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    key_fd = open("/dev/input/h432b-power", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (key_fd < 0) { r = -errno; goto out; }
    beep_fd = open("/dev/input/h432b-beeper", O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (beep_fd < 0) { r = -errno; goto out; }
    if (ioctl(key_fd, EVIOCSCLOCKID, &clock) < 0) { r = -errno; goto out; }
    tone = true; /* Explicitly silence inherited state on every start. */
    if ((r = set_tone(false)) < 0) goto out;
    if ((r = sd_bus_default_system(&bus)) < 0) goto out;
    if ((r = sd_bus_match_signal(bus, NULL, "org.freedesktop.login1",
        "/org/freedesktop/login1", "org.freedesktop.login1.Manager",
        "PrepareForSleep", prepare_sleep, NULL)) < 0) goto out;
    /* Keep logind's default handling as fallback if this service is absent.
     * This FD suppresses only physical-key policy, not Suspend/PowerOff APIs.
     */
    if ((r = sd_bus_call_method(bus, "org.freedesktop.login1",
        "/org/freedesktop/login1", "org.freedesktop.login1.Manager", "Inhibit",
        NULL, &reply, "ssss", "handle-power-key", "Fractal Microsystems",
        "Accessible power-button countdown", "block")) < 0) goto out;
    int received;
    if ((r = sd_bus_message_read(reply, "h", &received)) < 0) goto out;
    inhibitor = fcntl(received, F_DUPFD_CLOEXEC, 3);
    if (inhibitor < 0) { r = -errno; goto out; }
    reply = sd_bus_message_unref(reply);
    blocked = true; /* A button held during startup is never a new gesture. */
    ignore_until = now_ms() + 1000;
    while (!stopping) {
        do r = sd_bus_process(bus, NULL); while (r > 0);
        if (r < 0) break;
        if (stopping) { r = 0; break; }
        struct input_event ev;
        ssize_t n = -1;
        while (!stopping && (n = read(key_fd, &ev, sizeof(ev))) == (ssize_t)sizeof(ev)) {
            if (stopping) break;
            if (ev.type == EV_SYN && ev.code == SYN_DROPPED) {
                gesture_cancel(&gesture);
                blocked = true;
                ignore_until = now_ms() + 2000;
            }
            if (ev.type != EV_KEY || ev.code != KEY_POWER || ev.value == 2)
                continue;
            uint64_t stamp = (uint64_t)ev.input_event_sec * 1000 + ev.input_event_usec / 1000;
            if (sleeping || stamp < ignore_until || blocked) continue;
            if (ev.value == 1) gesture_press(&gesture, stamp);
            else if (ev.value == 0) {
                r = request_action(bus, gesture_release(&gesture, stamp));
                if (r < 0) goto out;
            }
        }
        if (stopping) { r = 0; break; }
        if (n >= 0 || (errno != EAGAIN && errno != EINTR)) {
            r = n >= 0 ? -EIO : -errno;
            break;
        }
        int down = key_down(key_fd);
        if (down < 0) { r = down; break; }
        if (stopping) { r = 0; break; }
        uint64_t now = now_ms();
        if (!sleeping && now >= ignore_until && !down) blocked = false;
        /* Never advance from a stale press when an input release was lost. */
        if (!down && gesture.active && !gesture.committed) gesture_cancel(&gesture);
        if (!sleeping && !blocked) {
            r = request_action(bus, gesture_tick(&gesture, now));
            if (r < 0) break;
        }
        if ((r = set_tone(gesture.tone)) < 0) break;
        int events = sd_bus_get_events(bus);
        if (events < 0) { r = events; break; }
        struct pollfd fds[] = {{key_fd, POLLIN, 0}, {sd_bus_get_fd(bus), events, 0}};
        int timeout = gesture.active ? 10 : 500;
        uint64_t bus_deadline;
        if (sd_bus_get_timeout(bus, &bus_deadline) >= 0 && bus_deadline != UINT64_MAX) {
            uint64_t delta = bus_deadline / 1000 > now ? bus_deadline / 1000 - now : 0;
            if (delta < (uint64_t)timeout) timeout = delta;
        }
        r = poll(fds, 2, timeout);
        if (r < 0 && errno != EINTR) { r = -errno; break; }
        if (r >= 0 && ((fds[0].revents | fds[1].revents) & (POLLHUP | POLLERR | POLLNVAL))) {
            r = -ENODEV; break;
        }
        r = 0;
    }
out:
    if (beep_fd >= 0) { set_tone(false); close(beep_fd); }
    if (key_fd >= 0) close(key_fd);
    if (inhibitor >= 0) close(inhibitor);
    sd_bus_message_unref(reply);
    sd_bus_unref(bus);
    if (r < 0) fprintf(stderr, "Power-key service: %s\n", strerror(-r));
    return r < 0 ? 1 : 0;
}
