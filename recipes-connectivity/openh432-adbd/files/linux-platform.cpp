// SPDX-License-Identifier: MIT
// Linux integration only. Authentication and RSA verification remain in AOSP.
#if defined(__ANDROID__) || defined(__ANDROID_RECOVERY__)
#error "This integration requires the authenticated non-Android daemon build"
#endif
#include <adbd_fs.h>
#include <cerrno>
#include <cstring>
#include <systemd/sd-daemon.h>
#include <sys/socket.h>

extern "C" int openh432_auth_socket(const char* name) {
    if (std::strcmp(name, "adbd") != 0 || sd_listen_fds(0) != 1 ||
        sd_is_socket_unix(SD_LISTEN_FDS_START, SOCK_SEQPACKET, 1,
                          "/run/openh432-adb/auth", 0) != 1) {
        errno = EINVAL;
        return -1;
    }
    return SD_LISTEN_FDS_START;
}

// Android's per-path UID/capability policy does not apply to Linux. The daemon
// is always unprivileged; file ownership/permissions are enforced by the kernel.
void adbd_fs_config(const char*, int, const char*, uid_t*, gid_t*, mode_t*, uint64_t*) {}
