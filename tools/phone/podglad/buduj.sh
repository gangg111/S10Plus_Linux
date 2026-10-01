#!/bin/bash
# Cross-build of the wayfire thumbnail plugin (podglad) against the phone sysroot.
set -e
mkdir -p ~/droidian/plasma/podglad
cp ~/droidian/podglad/podglad.cpp ~/droidian/plasma/podglad/
docker exec pmwf-krzyz bash -c '
set -e
export PKG_CONFIG_SYSROOT_DIR=/sysroot
export PKG_CONFIG_LIBDIR=/sysroot/usr/lib/aarch64-linux-gnu/pkgconfig:/sysroot/usr/lib/pkgconfig:/sysroot/usr/share/pkgconfig
cd /w/podglad
aarch64-linux-gnu-g++ --sysroot=/sysroot -std=c++17 -O2 -fPIC -shared \
    -DWLR_USE_UNSTABLE -DWAYFIRE_PLUGIN \
    $(pkg-config --cflags wayfire wf-config wlroots pixman-1 glesv2) \
    podglad.cpp -o libpodglad.so \
    -L/sysroot/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,/sysroot/usr/lib/aarch64-linux-gnu \
    -lGLESv2
chown 1000:1000 libpodglad.so
ls -la libpodglad.so
'
