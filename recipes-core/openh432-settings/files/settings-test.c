/* SPDX-License-Identifier: MIT */
#include "settings-store.h"
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    char path[] = "/tmp/fm-settings-test-XXXXXX";
    char *value = NULL;
    uint64_t revision;
    sqlite3 *db = NULL;
    const struct setting_definition *def = &settings_definitions[0];
    int fd = mkstemp(path);

    assert(fd >= 0);
    close(fd);
    assert(!settings_open(path, &db));
    assert(settings_find(def->scope, def->key) == def);
    assert(!settings_find("secure", def->key));
    assert(!settings_find("global", "unknown"));
    assert(!settings_get(db, def, &value) && !strcmp(value, "1"));
    free(value);
    assert(settings_write(db, def, "true", &revision) == -EINVAL);
    assert(settings_write(db, def, "1; DROP TABLE overrides", &revision) == -EINVAL);
    assert(!settings_write(db, def, "0", &revision) && revision == 1);
    assert(!settings_get(db, def, &value) && !strcmp(value, "0"));
    free(value);
    sqlite3_close(db);
    assert(!settings_open(path, &db));
    assert(!settings_get(db, def, &value) && !strcmp(value, "0"));
    free(value);
    assert(!settings_write(db, def, NULL, &revision) && revision == 2);
    assert(!settings_get(db, def, &value) && !strcmp(value, "1"));
    free(value);
    assert(sqlite3_exec(db, "UPDATE revision SET value=9223372036854775807", NULL, NULL, NULL) == SQLITE_OK);
    assert(settings_write(db, def, "0", &revision) == -EIO);
    assert(!settings_get(db, def, &value) && !strcmp(value, "1"));
    free(value);
    assert(sqlite3_exec(db, "PRAGMA user_version=2", NULL, NULL, NULL) == SQLITE_OK);
    sqlite3_close(db);
    assert(settings_open(path, &db) == -EIO && !db);
    unlink(path);
    return 0;
}
