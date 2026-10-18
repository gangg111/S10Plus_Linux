#!/bin/bash
# Cross-build of the S10Breeze Qt 6 widget style against the phone sysroot
# (container pmwf-krzyz, see tools/phone/podglad/buduj.sh).  Result:
# tools/phone/adaptacja/tools/qt6-styles/libs10style.so
set -e
TU=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/droidian/plasma/s10style
cp "$TU/s10style.cpp" "$TU/s10style.json" ~/droidian/plasma/s10style/
docker exec pmwf-krzyz bash -c '
set -e
export PKG_CONFIG_SYSROOT_DIR=/sysroot
export PKG_CONFIG_LIBDIR=/sysroot/usr/lib/aarch64-linux-gnu/pkgconfig:/sysroot/usr/lib/pkgconfig:/sysroot/usr/share/pkgconfig
cd /w/s10style
/usr/lib/qt6/libexec/moc $(pkg-config --cflags-only-I Qt6Widgets) s10style.cpp -o s10style.moc
aarch64-linux-gnu-g++ --sysroot=/sysroot -std=c++17 -O2 -fPIC -shared \
    $(pkg-config --cflags Qt6Widgets) \
    s10style.cpp -o libs10style.so \
    -L/sysroot/usr/lib/aarch64-linux-gnu -Wl,-rpath-link,/sysroot/usr/lib/aarch64-linux-gnu \
    $(pkg-config --libs Qt6Widgets)
chown 1000:1000 libs10style.so
'
mkdir -p "$TU/../adaptacja/tools/qt6-styles"
cp ~/droidian/plasma/s10style/libs10style.so "$TU/../adaptacja/tools/qt6-styles/"
ls -la "$TU/../adaptacja/tools/qt6-styles/libs10style.so"
