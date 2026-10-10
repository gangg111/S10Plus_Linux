#!/bin/bash
# Cross-build of the wayfire camera cutout plugin (wyciecie) against the phone sysroot.
# Usage in WSL: bash buduj-wyciecie.sh /path/to/wyciecie.cpp
set -e
SRC=${1:-~/droidian/podglad/wyciecie.cpp}
mkdir -p ~/droidian/plasma/podglad
cp "$SRC" ~/droidian/plasma/podglad/wyciecie.cpp
docker start pmwf-krzyz >/dev/null
docker exec pmwf-krzyz bash -c '
set -e
export PKG_CONFIG_SYSROOT_DIR=/sysroot
export PKG_CONFIG_LIBDIR=/sysroot/usr/lib/aarch64-linux-gnu/pkgconfig:/sysroot/usr/lib/pkgconfig:/sysroot/usr/share/pkgconfig
cd /w/podglad
aarch64-linux-gnu-g++ --sysroot=/sysroot -std=c++17 -O2 -fPIC -shared -Wall \
    -DWLR_USE_UNSTABLE -DWAYFIRE_PLUGIN \
    $(pkg-config --cflags wayfire wf-config wlroots pixman-1 glesv2) \
    wyciecie.cpp -o libwyciecie.so \
    -L/sysroot/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,/sysroot/usr/lib/aarch64-linux-gnu \
    -lGLESv2
chown 1000:1000 libwyciecie.so
ls -la libwyciecie.so
'
