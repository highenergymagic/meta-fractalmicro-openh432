/* SPDX-License-Identifier: MIT */
#include "settings-store.h"
#include "settings-bus.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <systemd/sd-bus.h>
#include <sys/stat.h>

/* The appliance account is explicitly UID 1000 in local-console policy.
 * Secure settings remain root-only until a reviewed authorization UI exists.
 */
static int authorize(sd_bus_message *m, const char *scope, bool write,
                     sd_bus_error *error)
{
    sd_bus_creds *creds = NULL;
    uid_t uid;
    int rc;

    if (strcmp(scope, "global") && strcmp(scope, "secure"))
        return sd_bus_error_set_const(error, SD_BUS_ERROR_INVALID_ARGS, "Unknown settings scope");
    rc = sd_bus_query_sender_creds(m, SD_BUS_CREDS_EUID, &creds);
    if (rc < 0)
        return rc;
    rc = sd_bus_creds_get_euid(creds, &uid);
    sd_bus_creds_unref(creds);
    if (rc < 0)
        return rc;
    if (uid == 0 || (!strcmp(scope, "global") && (!write || uid == 1000)))
        return 0;
    return sd_bus_error_set_const(error, SD_BUS_ERROR_ACCESS_DENIED, "Setting access denied");
}

static int handle(sd_bus_message *m, void *userdata, sd_bus_error *error)
{
    sqlite3 *db = userdata;
    const struct setting_definition *def;
    const char *scope, *key, *input = NULL, *member = sd_bus_message_get_member(m);
    bool write = !strcmp(member, "Put") || !strcmp(member, "Reset");
    uint64_t generation;
    char *value = NULL;
    int rc;

    rc = sd_bus_message_read(m, "ss", &scope, &key);
    if (rc < 0)
        return rc;
    rc = authorize(m, scope, write, error);
    if (rc < 0)
        return rc;
    def = settings_find(scope, key);
    if (!def)
        return sd_bus_error_set_const(error, SD_BUS_ERROR_INVALID_ARGS, "Unknown settings key");
    if (!strcmp(member, "Put")) {
        rc = sd_bus_message_read(m, "s", &input);
        if (rc < 0)
            return rc;
    }
    if (write) {
        rc = settings_write(db, def, input, &generation);
        if (rc == -EINVAL)
            return sd_bus_error_set_const(error, SD_BUS_ERROR_INVALID_ARGS, "Invalid setting value");
        if (rc < 0)
            return sd_bus_error_set_const(error, SD_BUS_ERROR_FAILED, "Settings transaction failed");
        /* Secure values never appear on a broadcast signal. */
        if (!strcmp(scope, "global")) {
            rc = sd_bus_emit_signal(sd_bus_message_get_bus(m), SETTINGS_PATH,
                                    SETTINGS_INTERFACE, "Changed", "ssst", scope,
                                    key, input ? input : def->initial, generation);
            if (rc < 0)
                fprintf(stderr, "Settings notification failed: %s\n", strerror(-rc));
        }
        return sd_bus_reply_method_return(m, "t", generation);
    }
    rc = settings_get(db, def, &value);
    if (rc < 0)
        return sd_bus_error_set_const(error, SD_BUS_ERROR_FAILED, "Settings read failed");
    rc = sd_bus_reply_method_return(m, "s", value);
    free(value);
    return rc;
}

static int list(sd_bus_message *m, void *userdata, sd_bus_error *error)
{
    sqlite3 *db = userdata;
    sd_bus_message *reply = NULL;
    const char *scope;
    char *value = NULL;
    int rc = sd_bus_message_read(m, "s", &scope);

    if (rc < 0)
        return rc;
    rc = authorize(m, scope, false, error);
    if (rc < 0)
        return rc;
    rc = sd_bus_message_new_method_return(m, &reply);
    if (rc < 0)
        goto out;
    rc = sd_bus_message_open_container(reply, 'a', "{ss}");
    if (rc < 0)
        goto out;
    for (unsigned i = 0; i < settings_count; i++) {
        const struct setting_definition *def = &settings_definitions[i];
        if (strcmp(scope, def->scope))
            continue;
        rc = settings_get(db, def, &value);
        if (rc < 0)
            goto out;
        rc = sd_bus_message_append(reply, "{ss}", def->key, value);
        free(value);
        value = NULL;
        if (rc < 0)
            goto out;
    }
    rc = sd_bus_message_close_container(reply);
    if (rc >= 0)
        rc = sd_bus_send(NULL, reply, NULL);
out:
    free(value);
    sd_bus_message_unref(reply);
    return rc;
}

static const sd_bus_vtable vtable[] = {
    SD_BUS_VTABLE_START(0),
    SD_BUS_METHOD("Get", "ss", "s", handle, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("Put", "sss", "t", handle, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("Reset", "ss", "t", handle, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("List", "s", "a{ss}", list, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_SIGNAL("Changed", "ssst", 0),
    SD_BUS_VTABLE_END
};

int main(void)
{
    sd_bus *bus = NULL;
    sqlite3 *db = NULL;
    int rc;

    umask(0077);
    rc = settings_open("/var/lib/fractalmicro/settings/settings.db", &db);
    if (rc < 0)
        goto out;
    rc = sd_bus_open_system(&bus);
    if (rc < 0)
        goto out;
    rc = sd_bus_add_object_vtable(bus, NULL, SETTINGS_PATH, SETTINGS_INTERFACE, vtable, db);
    if (rc < 0)
        goto out;
    rc = sd_bus_request_name(bus, SETTINGS_BUS, 0);
    if (rc < 0)
        goto out;
    for (;;) {
        rc = sd_bus_process(bus, NULL);
        if (rc < 0)
            break;
        if (rc > 0)
            continue;
        rc = sd_bus_wait(bus, UINT64_MAX);
        if (rc < 0)
            break;
    }
out:
    if (rc < 0)
        fprintf(stderr, "Settings service failed: %s\n", strerror(-rc));
    sd_bus_flush_close_unref(bus);
    if (db)
        sqlite3_close(db);
    return rc < 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
