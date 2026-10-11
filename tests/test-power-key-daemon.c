// SPDX-License-Identifier: MIT
/* Run the real daemon against deterministic syscall and D-Bus doubles. */
#define _GNU_SOURCE
#include <assert.h>
#include <stdarg.h>
#include <stdlib.h>
#define main power_key_daemon_main
#include "../recipes-core/openh432-power-key/files/openh432-power-key.c"
#undef main

enum scenario { KEY_OPEN_FAIL, BEEPER_OPEN_FAIL, STOP_BUS, STOP_RELEASE, STOP_IOCTL };
static enum scenario scenario;
static int key_opens, beeper_opens, key_closes, beeper_closes, actions;
static unsigned phase, reads;
static uint64_t test_now = 0;
static struct sd_bus test_bus;
static struct sd_bus_message test_message;

int __wrap_open(const char *path, int flags, ...)
{
    (void)flags;
    if (!strcmp(path, "/dev/input/h432b-power")) {
        key_opens++;
        if (scenario == KEY_OPEN_FAIL) { errno = ENOENT; return -1; }
        return 10;
    }
    assert(!strcmp(path, "/dev/input/h432b-beeper"));
    beeper_opens++;
    if (scenario == BEEPER_OPEN_FAIL) { errno = EACCES; return -1; }
    /* A successful call need not preserve an earlier errno. */
    errno = 0;
    return 11;
}
int __wrap_close(int fd)
{
    if (fd == 10) key_closes++;
    else if (fd == 11) beeper_closes++;
    else assert(fd == 12);
    return 0;
}
int __wrap_fcntl(int fd, int command, ...)
{
    assert(fd == 13 && command == F_DUPFD_CLOEXEC);
    return 12;
}
int __wrap_clock_gettime(clockid_t clock, struct timespec *t)
{
    assert(clock == CLOCK_MONOTONIC);
    t->tv_sec = test_now / 1000;
    t->tv_nsec = (test_now % 1000) * 1000000;
    return 0;
}
int __wrap_ioctl(int fd, unsigned long request, ...)
{
    va_list ap;
    va_start(ap, request);
    void *arg = va_arg(ap, void *);
    va_end(ap);
    assert(fd == 10);
    if (request == EVIOCSCLOCKID) return 0;
    assert(_IOC_NR(request) == _IOC_NR(EVIOCGKEY(0)));
    memset(arg, 0, _IOC_SIZE(request));
    if (phase == 1) ((unsigned char *)arg)[KEY_POWER / 8] |= 1U << (KEY_POWER % 8);
    if (scenario == STOP_IOCTL && phase == 1) raise(SIGTERM);
    return 0;
}
ssize_t __wrap_write(int fd, const void *data, size_t size)
{
    assert(fd == 11 && size == sizeof(struct input_event));
    const struct input_event *ev = data;
    assert(ev->type == EV_SND && ev->code == SND_BELL);
    assert(!stopping || ev->value == 0);
    return size;
}
ssize_t __wrap_read(int fd, void *data, size_t size)
{
    assert(fd == 10 && size == sizeof(struct input_event));
    if (phase == 0 || reads++) { errno = EAGAIN; return -1; }
    struct input_event *ev = data;
    *ev = (struct input_event){ .type = EV_KEY, .code = KEY_POWER,
                               .value = phase == 1 ? 1 : 0 };
    ev->input_event_sec = test_now / 1000;
    ev->input_event_usec = (test_now % 1000) * 1000;
    if (scenario == STOP_RELEASE && phase == 2) raise(SIGTERM);
    return size;
}
int __wrap_poll(struct pollfd *fds, nfds_t n, int timeout)
{
    (void)fds; (void)timeout;
    assert(n == 2 && phase < 2 && !stopping);
    phase++;
    reads = 0;
    test_now = phase == 1 ? 2000 : 2100;
    return 0;
}
int sd_bus_default_system(sd_bus **bus) { *bus = &test_bus; return 0; }
int sd_bus_match_signal(sd_bus *b, void *s, const char *sender, const char *path,
                        const char *interface, const char *member,
                        sd_bus_message_handler_t handler, void *userdata) { return 0; }
int sd_bus_call_method(sd_bus *b, const char *d, const char *p, const char *i,
                       const char *member, sd_bus_error *error,
                       sd_bus_message **reply, const char *types, ...)
{
    assert(!strcmp(member, "Inhibit"));
    *reply = &test_message;
    return 0;
}
int sd_bus_call_method_async(sd_bus *b, void *slot, const char *d, const char *p,
                             const char *i, const char *member,
                             sd_bus_message_handler_t handler, void *userdata,
                             const char *types, ...)
{
    actions++;
    return 0;
}
int sd_bus_message_read(sd_bus_message *m, const char *types, ...)
{
    va_list ap;
    va_start(ap, types);
    *va_arg(ap, int *) = 13;
    va_end(ap);
    return 1;
}
const sd_bus_error *sd_bus_message_get_error(sd_bus_message *m) { return NULL; }
sd_bus_message *sd_bus_message_unref(sd_bus_message *m) { return NULL; }
sd_bus *sd_bus_unref(sd_bus *b) { return NULL; }
int sd_bus_process(sd_bus *b, sd_bus_message **reply)
{
    if (scenario == STOP_BUS) raise(SIGTERM);
    if (phase == 0) test_now = 1000; /* End startup-held-key exclusion. */
    return 0;
}
int sd_bus_get_events(sd_bus *b) { return POLLIN; }
int sd_bus_get_fd(sd_bus *b) { return 14; }
int sd_bus_get_timeout(sd_bus *b, uint64_t *timeout) { *timeout = UINT64_MAX; return 0; }

int main(int argc, char **argv)
{
    assert(argc == 2);
    scenario = atoi(argv[1]);
    assert(scenario <= STOP_IOCTL);
    int result = power_key_daemon_main();
    assert(key_opens == 1 && actions == 0);
    if (scenario == KEY_OPEN_FAIL) {
        assert(result == 1 && beeper_opens == 0 && key_closes == 0);
    } else if (scenario == BEEPER_OPEN_FAIL) {
        assert(result == 1 && beeper_opens == 1 && key_closes == 1 && beeper_closes == 0);
    } else {
        assert(result == 0 && key_closes == 1 && beeper_closes == 1);
        assert(stopping && !tone);
    }
    return 0;
}
