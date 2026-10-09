#!/bin/bash
# Cross build of plasma-settings (v26.04.0, One UI look) in the pmwf-krzyz container, incremental.
# Source: ~/droidian/plasma/plasma-settings (= /w/plasma-settings), build dir /w/obj-ps.
B=/w/obj-ps
docker start pmwf-krzyz >/dev/null
docker exec pmwf-krzyz bash -c "
set -e
if [ ! -f $B/build.ninja ]; then
    cmake -G Ninja -S /w/plasma-settings -B $B \
        -DCMAKE_TOOLCHAIN_FILE=/w/toolchain-s10.cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_INSTALL_LIBDIR=lib/aarch64-linux-gnu \
        -DQUERY_EXECUTABLE=/usr/bin/x86_64-linux-gnu-qtpaths6 \
        -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF \
        -DKDE_INSTALL_QMLDIR=lib/aarch64-linux-gnu/qt6/qml \
        -DKDE_INSTALL_QTPLUGINDIR=lib/aarch64-linux-gnu/qt6/plugins \
        -DKDE_INSTALL_DATAROOTDIR=share \
        -DBUILD_TESTING=OFF > /w/ps-cmake.log 2>&1 || { grep -E 'CMake Error|Could not find|not found' -A3 /w/ps-cmake.log | head -40; exit 1; }
    echo 'cmake OK'
fi
start=\$(date +%s)
ninja -C $B plasma-settings > /w/ps-ninja.log 2>&1 || { grep -m20 -E 'error|FAILED|Error' /w/ps-ninja.log; exit 1; }
echo \"ninja OK w \$(( \$(date +%s) - start )) s\"
ls -la $B/bin/plasma-settings
"
