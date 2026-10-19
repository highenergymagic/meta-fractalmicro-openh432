# SPDX-License-Identifier: MIT
cmake_minimum_required(VERSION 3.22)
project(openh432_adbd LANGUAGES C CXX ASM)
include(GNUInstallDirs)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Threads REQUIRED)
find_package(fmt REQUIRED)
find_package(Protobuf REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(SYSTEMD REQUIRED IMPORTED_TARGET libsystemd)
pkg_check_modules(BROTLI REQUIRED IMPORTED_TARGET libbrotlidec libbrotlienc)
pkg_check_modules(LZ4 REQUIRED IMPORTED_TARGET liblz4)
pkg_check_modules(ZSTD REQUIRED IMPORTED_TARGET libzstd)
set(BUILD_SHARED_LIBS OFF)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(boringssl EXCLUDE_FROM_ALL)
add_compile_definitions(_GNU_SOURCE ADB_HOST=0)
add_compile_options("$<$<COMPILE_LANGUAGE:CXX>:-include${CMAKE_CURRENT_SOURCE_DIR}/gcc-compat.h>")
include_directories(libbase/include logging/liblog/include core/libcutils/include
  core/libutils/include core/include core/libcrypto_utils/include core/libasyncio/include core/diagnose_usb/include
  adb adb/crypto/include adb/tls/include adb/libs/libadbd_fs/include
  native/libs/adbd_auth/include boringssl/include ${CMAKE_CURRENT_BINARY_DIR})
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/platform_tools_version.h
  "#define PLATFORM_TOOLS_VERSION \"Android 16 OpenH432\"\n")
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/build)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/build/version.h
  "#pragma once\n#include <string>\nnamespace android::build { inline std::string GetBuildNumber() { return \"android-16.0.0_r4\"; } }\n")
protobuf_generate_cpp(PROTO_SRC PROTO_HDR adb/proto/key_type.proto)
add_library(android_support STATIC
  libbase/chrono_utils.cpp libbase/cmsg.cpp libbase/file.cpp libbase/hex.cpp
  libbase/logging.cpp libbase/mapped_file.cpp libbase/parsebool.cpp
  libbase/parsenetaddress.cpp libbase/posix_strerror_r.cpp libbase/process.cpp
  libbase/properties.cpp libbase/result.cpp libbase/stringprintf.cpp
  libbase/strings.cpp libbase/threads.cpp libbase/errors_unix.cpp
  logging/liblog/log_event_list.cpp logging/liblog/log_event_write.cpp
  logging/liblog/logger_name.cpp logging/liblog/logger_read.cpp
  logging/liblog/logger_write.cpp logging/liblog/properties.cpp logging/liblog/logprint.cpp
  core/libcutils/socket_inaddr_any_server_unix.cpp core/libcutils/socket_local_client_unix.cpp
  core/libcutils/socket_local_server_unix.cpp core/libcutils/socket_network_client_unix.cpp
  core/libcutils/sockets_unix.cpp core/libcutils/sockets.cpp
  core/libcrypto_utils/android_pubkey.cpp core/libasyncio/AsyncIO.cpp
  core/diagnose_usb/diagnose_usb.cpp
  native/libs/adbd_auth/adbd_auth.cpp linux-platform.cpp)
target_compile_definitions(android_support PRIVATE LIBLOG_LOG_TAG=1006 FAKE_LOG_DEVICE=1)
target_link_libraries(android_support PUBLIC fmt::fmt crypto PkgConfig::SYSTEMD Threads::Threads)
add_executable(adbd
  adb/adb.cpp adb/adb_io.cpp adb/adb_listeners.cpp adb/adb_trace.cpp
  adb/adb_unique_fd.cpp adb/adb_utils.cpp adb/apacket_reader.cpp
  adb/fdevent/fdevent.cpp adb/fdevent/fdevent_epoll.cpp
  adb/services.cpp adb/sockets.cpp adb/socket_spec.cpp
  adb/sysdeps/env.cpp adb/sysdeps/errno.cpp adb/sysdeps_unix.cpp
  adb/sysdeps/posix/network.cpp adb/transport.cpp adb/transport_fd.cpp adb/types.cpp
  adb/daemon/adb_wifi.cpp adb/daemon/auth.cpp adb/daemon/jdwp_service.cpp
  adb/daemon/logging.cpp adb/daemon/transport_socket_server.cpp
  adb/daemon/file_sync_service.cpp adb/daemon/services.cpp adb/daemon/shell_service.cpp
  adb/daemon/tradeinmode.cpp adb/shell_service_protocol.cpp
  adb/daemon/usb.cpp adb/daemon/usb_ffs.cpp adb/daemon/main.cpp
  adb/crypto/key.cpp adb/crypto/rsa_2048_key.cpp adb/crypto/x509_generator.cpp
  adb/tls/adb_ca_list.cpp adb/tls/tls_connection.cpp ${PROTO_SRC})
target_compile_definitions(adbd PRIVATE ANDROID_BASE_UNIQUE_FD_DISABLE_IMPLICIT_CONVERSION=1)
# Load streams before ADB poisons raw POSIX names. Do not apply to libbase:
# posix_strerror_r.cpp must undefine _GNU_SOURCE before its first libc header.
target_compile_options(adbd PRIVATE "SHELL:-include sstream" "SHELL:-include iostream")
# There is no Android VM/process tracking on this Linux appliance. Apply the
# upstream no-JDWP implementation ONLY to this translation unit, never auth/main.
set_source_files_properties(adb/daemon/jdwp_service.cpp PROPERTIES
  COMPILE_DEFINITIONS __ANDROID_RECOVERY__)
target_link_libraries(adbd PRIVATE android_support ssl crypto protobuf::libprotobuf-lite
  PkgConfig::BROTLI PkgConfig::LZ4 PkgConfig::ZSTD resolv util cap)
install(TARGETS adbd RUNTIME DESTINATION ${CMAKE_INSTALL_SBINDIR})
