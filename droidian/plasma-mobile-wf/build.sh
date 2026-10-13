#!/bin/bash
# plasma-mobile-wf of the port: the Droidian shell (Plasma Mobile on wayfire) at a pinned
# commit plus plasma-mobile-wf/patches (Plasma 6.7 and Qt 6.11, One UI quick settings and
# task switcher, status bar clear of the camera hole, network technology, ...).
# Builds plasma-mobile-wf, -config-hwcomposer and -tweaks.
#
# Usage: ./build.sh      -> $LOCALREPO/plasma-mobile-wf*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"

S=$WORK/src/plasma-mobile-wf
log "plasma-mobile-wf at ${SHELL_BASE:0:12}"
fetch_at "$SHELL_REPO" "$SHELL_BASE" "$S"
log "applying $(ls "$DROIDIAN_DIR"/plasma-mobile-wf/patches/*.patch | wc -l) patches"
apply_series "$S" "$DROIDIAN_DIR"/plasma-mobile-wf/patches/*.patch
"$DROIDIAN_DIR/build-arm64.sh" "$S"
