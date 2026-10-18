#!/bin/bash
# The camera app of the port: droidian-camera at a pinned commit plus the patches in
# tools/phone/aparat/patches (full Camera1 HAL, a Camera2 path with manual ISO, shutter
# and focus, RAW as DNG, live PRO and video session, One UI style settings, ...).
#
# Its libcamx.so runs on the Android side and is linked against the phone's own Android
# libraries (see "Android libraries" in ../README.md); without them CMake would only warn
# and build a camera with no PRO modes and no video, so this script stops instead.
#
# Usage: ANDROID_LIBS=<dir> ./build.sh      -> $LOCALREPO/droidian-camera_*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"

NEEDED="libcamera_client.so libutils.so libcamera2ndk.so libmediandk.so libbinder_ndk.so
libnativewindow.so libc++.so libc.so libm.so"
[ -n "${ANDROID_LIBS:-}" ] || die "ANDROID_LIBS is not set: the directory with the Android libraries of an S10+ (see README)"
ANDROID_LIBS=$(cd "$ANDROID_LIBS" && pwd)
for f in $NEEDED; do
	[ -f "$ANDROID_LIBS/$f" ] || die "$ANDROID_LIBS/$f is missing (see README, Android libraries)"
done
export ANDROID_LIBS

S=$WORK/src/droidian-camera
log "droidian-camera at ${CAMERA_BASE:0:12}"
fetch_at "$CAMERA_REPO" "$CAMERA_BASE" "$S"
log "applying $(ls "$REPO_DIR"/tools/phone/aparat/patches/*.patch | wc -l) patches"
apply_series "$S" "$REPO_DIR"/tools/phone/aparat/patches/*.patch
"$DROIDIAN_DIR/build-arm64.sh" "$S"

deb=$(ls -t "$WORK"/src/droidian-camera_*_arm64.deb | head -1)
# the listing is read whole: grep -q would close the pipe early and, with pipefail,
# dpkg-deb's broken pipe would count as a failure
contents=$(dpkg-deb -c "$deb")
grep -q '/usr/lib/droidian-camera/libcamx.so$' <<<"$contents" \
	|| die "$(basename "$deb") has no libcamx.so (PRO modes and video would not work)"
log "libcamx.so is in $(basename "$deb")"
