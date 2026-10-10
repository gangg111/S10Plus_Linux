#!/bin/bash
# Cross-build of the wayfire rotation plugin (obrot) against the phone sysroot.
# Usage in WSL: bash buduj-obrot.sh /path/to/obrot.cpp
set -e
SRC=${1:-~/droidian/podglad/obrot.cpp}
mkdir -p ~/droidian/plasma/podglad
cp "$SRC" ~/droidian/plasma/podglad/obrot.cpp
docker start pmwf-krzyz >/dev/null
docker exec pmwf-krzyz bash -c '
set -e
export PKG_CONFIG_SYSROOT_DIR=/sysroot
export PKG_CONFIG_LIBDIR=/sysroot/usr/lib/aarch64-linux-gnu/pkgconfig:/sysroot/usr/lib/pkgconfig:/sysroot/usr/share/pkgconfig
cd /w/podglad
aarch64-linux-gnu-g++ --sysroot=/sysroot -std=c++17 -O2 -fPIC -shared -Wall \
    -DWLR_USE_UNSTABLE -DWAYFIRE_PLUGIN \
    $(pkg-config --cflags wayfire wf-config wlroots pixman-1 glesv2 gio-2.0) \
    obrot.cpp -o libobrot.so \
    -L/sysroot/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,/sysroot/usr/lib/aarch64-linux-gnu \
    -lGLESv2 -lgio-2.0 -lgobject-2.0 -lglib-2.0
chown 1000:1000 libobrot.so
ls -la libobrot.so
'
