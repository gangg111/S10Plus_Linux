#!/bin/bash
# The camera app of the port: droidian-camera at a pinned commit plus the patches in
# tools/phone/aparat/patches (full Camera1 HAL, a Camera2 path with manual ISO, shutter
# and focus, RAW as DNG, live PRO and video session, One UI style settings, ...).
#
# Usage: ./build.sh      -> $LOCALREPO/droidian-camera_*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"

S=$WORK/src/droidian-camera
log "droidian-camera at ${CAMERA_BASE:0:12}"
fetch_at "$CAMERA_REPO" "$CAMERA_BASE" "$S"
log "applying $(ls "$REPO_DIR"/tools/phone/aparat/patches/*.patch | wc -l) patches"
apply_series "$S" "$REPO_DIR"/tools/phone/aparat/patches/*.patch
"$DROIDIAN_DIR/build-arm64.sh" "$S"
