/* SPDX-License-Identifier: MIT */
#ifndef FM_SETTINGS_STORE_H
#define FM_SETTINGS_STORE_H
#include <stdbool.h>
#include <stdint.h>
#include <sqlite3.h>
struct setting_definition {
    const char *scope, *key, *initial;
    bool boolean;
};
extern const struct setting_definition settings_definitions[];
extern const unsigned settings_count;
const struct setting_definition *settings_find(const char *scope, const char *key);
int settings_open(const char *path, sqlite3 **db);
int settings_get(sqlite3 *db, const struct setting_definition *def, char **value);
int settings_write(sqlite3 *db, const struct setting_definition *def,
                   const char *value, uint64_t *generation);
#endif
