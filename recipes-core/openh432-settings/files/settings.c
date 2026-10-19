/* SPDX-License-Identifier: MIT */
#include "settings-bus.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <systemd/sd-bus.h>

int main(int argc, char **argv)
{
    sd_bus *bus = NULL;
    sd_bus_message *reply = NULL;
    sd_bus_error error = SD_BUS_ERROR_NULL;
    const char *method, *value, *key;
    int rc;

    if (argc == 3 && !strcmp(argv[1], "list"))
        method = "List";
    else if (argc == 4 && !strcmp(argv[1], "get"))
        method = "Get";
    else if (argc == 4 && !strcmp(argv[1], "reset"))
        method = "Reset";
    else if (argc == 5 && !strcmp(argv[1], "put"))
        method = "Put";
    else {
        fprintf(stderr, "Usage: settings list SCOPE | get SCOPE KEY | put SCOPE KEY VALUE | reset SCOPE KEY\n");
        return 2;
    }
    rc = sd_bus_open_system(&bus);
    if (rc < 0)
        goto out;
    sd_bus_set_method_call_timeout(bus, 5000000);
    rc = sd_bus_call_method(bus, SETTINGS_BUS, SETTINGS_PATH, SETTINGS_INTERFACE,
                            method, &error, &reply, argc == 3 ? "s" :
                            argc == 4 ? "ss" : "sss", argv[2],
                            argc > 3 ? argv[3] : NULL, argc > 4 ? argv[4] : NULL);
    if (rc < 0)
        goto out;
    if (!strcmp(method, "Get")) {
        rc = sd_bus_message_read(reply, "s", &value);
        if (rc > 0)
            puts(value);
    } else if (!strcmp(method, "List")) {
        rc = sd_bus_message_enter_container(reply, 'a', "{ss}");
        if (rc < 0)
            goto out;
        while ((rc = sd_bus_message_read(reply, "{ss}", &key, &value)) > 0)
            printf("%s=%s\n", key, value);
    }
out:
    if (rc < 0)
        fprintf(stderr, "settings: %s\n", error.message ? error.message : strerror(-rc));
    sd_bus_error_free(&error);
    sd_bus_message_unref(reply);
    sd_bus_flush_close_unref(bus);
    return rc < 0 ? 1 : 0;
}
