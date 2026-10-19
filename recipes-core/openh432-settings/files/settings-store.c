/* SPDX-License-Identifier: MIT */
#include "settings-store.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

/* Preferences only: consumers must explicitly implement their application. */
const struct setting_definition settings_definitions[] = {
    { "global", "org.fractalmicro.braille.BrailleDisplayEnableEightDotMode", "1", true },
    { "secure", "org.fractalmicro.usb.DebuggingEnabled", "0", true },
};
const unsigned settings_count = sizeof(settings_definitions) / sizeof(settings_definitions[0]);

const struct setting_definition *settings_find(const char *scope, const char *key)
{
    for (unsigned i = 0; i < settings_count; i++)
        if (!strcmp(scope, settings_definitions[i].scope) &&
            !strcmp(key, settings_definitions[i].key))
            return &settings_definitions[i];
    return NULL;
}

static int sql(sqlite3 *db, const char *text)
{
    return sqlite3_exec(db, text, NULL, NULL, NULL) == SQLITE_OK ? 0 : -EIO;
}

int settings_open(const char *path, sqlite3 **db)
{
    sqlite3_stmt *st = NULL;
    int rc, version;

    *db = NULL;
    if (sqlite3_open_v2(path, db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE |
                       SQLITE_OPEN_NOFOLLOW, NULL) != SQLITE_OK)
        goto fail;
    sqlite3_busy_timeout(*db, 2000);
    if (sqlite3_prepare_v2(*db, "PRAGMA user_version", -1, &st, NULL) != SQLITE_OK)
        goto fail;
    rc = sqlite3_step(st);
    version = rc == SQLITE_ROW ? sqlite3_column_int(st, 0) : -1;
    sqlite3_finalize(st);
    st = NULL;
    /* Never silently downgrade a future schema during A/B rollback. */
    if (version != 0 && version != 1)
        goto fail;
    if (sql(*db, "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;"
                 "PRAGMA trusted_schema=OFF; BEGIN IMMEDIATE;"
                 "CREATE TABLE IF NOT EXISTS overrides (scope TEXT NOT NULL,"
                 "key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(scope,key));"
                 "CREATE TABLE IF NOT EXISTS revision (id INTEGER PRIMARY KEY "
                 "CHECK(id=1), value INTEGER NOT NULL CHECK(value>=0));"
                 "INSERT OR IGNORE INTO revision VALUES(1,0);"
                 "PRAGMA user_version=1; COMMIT;"))
        goto fail;
    return 0;
fail:
    sqlite3_finalize(st);
    if (*db)
        sqlite3_close(*db);
    *db = NULL;
    return -EIO;
}

int settings_get(sqlite3 *db, const struct setting_definition *def, char **value)
{
    sqlite3_stmt *st = NULL;
    const unsigned char *text;
    int rc, result = -EIO;

    *value = NULL;
    if (sqlite3_prepare_v2(db, "SELECT value FROM overrides WHERE scope=? AND key=?",
                         -1, &st, NULL) != SQLITE_OK)
        return -EIO;
    sqlite3_bind_text(st, 1, def->scope, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, def->key, -1, SQLITE_STATIC);
    rc = sqlite3_step(st);
    if (rc == SQLITE_ROW || rc == SQLITE_DONE) {
        text = rc == SQLITE_ROW ? sqlite3_column_text(st, 0) :
                                 (const unsigned char *) def->initial;
        if (text && (!def->boolean || !strcmp((const char *)text, "0") ||
                      !strcmp((const char *)text, "1"))) {
            *value = strdup((const char *) text);
            result = *value ? 0 : -ENOMEM;
        }
    }
    sqlite3_finalize(st);
    return result;
}

int settings_write(sqlite3 *db, const struct setting_definition *def,
                   const char *value, uint64_t *generation)
{
    sqlite3_stmt *st = NULL;
    const char *statement = value ?
        "INSERT INTO overrides VALUES(?,?,?) ON CONFLICT(scope,key) DO UPDATE SET value=excluded.value" :
        "DELETE FROM overrides WHERE scope=? AND key=?";

    if (value && (strlen(value) > 4096 || (def->boolean &&
        strcmp(value, "0") && strcmp(value, "1"))))
        return -EINVAL;
    if (sql(db, "BEGIN IMMEDIATE"))
        return -EIO;
    if (sqlite3_prepare_v2(db, statement, -1, &st, NULL) != SQLITE_OK)
        goto fail;
    sqlite3_bind_text(st, 1, def->scope, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, def->key, -1, SQLITE_STATIC);
    if (value)
        sqlite3_bind_text(st, 3, value, -1, SQLITE_STATIC);
    if (sqlite3_step(st) != SQLITE_DONE)
        goto fail;
    sqlite3_finalize(st);
    st = NULL;
    if (sql(db, "UPDATE revision SET value=value+1 WHERE id=1 AND value<9223372036854775807") ||
        sqlite3_changes(db) != 1)
        goto fail;
    if (sqlite3_prepare_v2(db, "SELECT value FROM revision WHERE id=1", -1, &st, NULL) != SQLITE_OK ||
        sqlite3_step(st) != SQLITE_ROW)
        goto fail;
    *generation = (uint64_t) sqlite3_column_int64(st, 0);
    sqlite3_finalize(st);
    st = NULL;
    if (!sql(db, "COMMIT"))
        return 0;
fail:
    sqlite3_finalize(st);
    sql(db, "ROLLBACK");
    return -EIO;
}
