#!/bin/bash
# Cross build of Pobieranie in the pmwf-krzyz container (phone sysroot, toolchain-s10.cmake).
# Run in WSL: bash buduj.sh <path of tools/phone/pobieranie>. Result: ~/droidian/plasma/obj-pob/pobieranie
set -e
SRC=${1:-/mnt/c/Users/Artur/Documents/Serwis/Programowanie/S10Plus_Linux/tools/phone/pobieranie}
rm -rf ~/droidian/plasma/pobieranie
mkdir -p ~/droidian/plasma/pobieranie/qml
cp "$SRC"/CMakeLists.txt "$SRC"/main.cpp "$SRC"/pobieranie.qrc ~/droidian/plasma/pobieranie/
cp "$SRC"/qml/* ~/droidian/plasma/pobieranie/qml/
sed -i 's/\r$//' ~/droidian/plasma/pobieranie/*.* ~/droidian/plasma/pobieranie/qml/*
docker start pmwf-krzyz >/dev/null
docker exec pmwf-krzyz bash -c '
set -e
B=/w/obj-pob
# syntax of every QML file first (errors only; imports of the phone are not resolvable here)
for f in /w/pobieranie/qml/*.qml; do
    /usr/lib/qt6/bin/qmlformat "$f" > /dev/null 2> /tmp/qmlformat.err || { echo "QML: $f"; cat /tmp/qmlformat.err; exit 1; }
done
if [ ! -f $B/build.ninja ]; then
    cmake -G Ninja -S /w/pobieranie -B $B -DCMAKE_TOOLCHAIN_FILE=/w/toolchain-s10.cmake \
        -DCMAKE_BUILD_TYPE=Release > /w/pob-cmake.log 2>&1 || { grep -E "CMake Error|Could not find|not found" -A3 /w/pob-cmake.log | head -30; exit 1; }
fi
s=$(date +%s)
ninja -C $B > /w/pob-ninja.log 2>&1 || { grep -E "error|FAILED|warning" /w/pob-ninja.log | head -30; exit 1; }
grep -c "warning" /w/pob-ninja.log || true
echo "ninja OK w $(( $(date +%s) - s )) s"
ls -la $B/pobieranie
'
