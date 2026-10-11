/* SPDX-License-Identifier: MIT */
/* Minimal test double; production builds use libsystemd's real header. */
#ifndef TEST_SD_BUS_H
#define TEST_SD_BUS_H
#include <stdint.h>
typedef struct sd_bus { int unused; } sd_bus;
typedef struct sd_bus_message { int unused; } sd_bus_message;
typedef struct sd_bus_error { const char *message; } sd_bus_error;
typedef int (*sd_bus_message_handler_t)(sd_bus_message *, void *, sd_bus_error *);
int sd_bus_default_system(sd_bus **bus);
int sd_bus_match_signal(sd_bus *, void *, const char *, const char *, const char *,
                        const char *, sd_bus_message_handler_t, void *);
int sd_bus_call_method(sd_bus *, const char *, const char *, const char *, const char *,
                       sd_bus_error *, sd_bus_message **, const char *, ...);
int sd_bus_call_method_async(sd_bus *, void *, const char *, const char *, const char *,
                             const char *, sd_bus_message_handler_t, void *, const char *, ...);
int sd_bus_message_read(sd_bus_message *, const char *, ...);
const sd_bus_error *sd_bus_message_get_error(sd_bus_message *);
sd_bus_message *sd_bus_message_unref(sd_bus_message *);
sd_bus *sd_bus_unref(sd_bus *);
int sd_bus_process(sd_bus *, sd_bus_message **);
int sd_bus_get_events(sd_bus *);
int sd_bus_get_fd(sd_bus *);
int sd_bus_get_timeout(sd_bus *, uint64_t *);
#endif
