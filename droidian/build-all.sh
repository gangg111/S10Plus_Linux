#!/bin/bash
# Builds every package of the port into the local repository, in dependency order, then
# the image.  Each step can also be run on its own (see README.md).
#
# Usage: ABOX_FIRMWARE=/path/to/abox-fw ./build-all.sh
set -euo pipefail
. "$(dirname "$0")/env.sh"
: "${ABOX_FIRMWARE:?set ABOX_FIRMWARE first (see README.md, step 2)}"

command -v docker >/dev/null || die "docker is needed"
[ -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ] || die "arm64 emulation is not registered (README.md, step 1)"
mkdir -p "$LOCALREPO"

"$DROIDIAN_DIR/kernel/build.sh"
"$DROIDIAN_DIR/archive-rebuild/build.sh"
"$DROIDIAN_DIR/plasma-mobile-wf/build.sh"
"$DROIDIAN_DIR/camera/build.sh"
"$DROIDIAN_DIR/adaptation/build.sh"
log "libbatman-wrappers placeholder"
in_container "$IMG_AMD64" linux/amd64 -v "$DROIDIAN_DIR":/d:ro -v "$LOCALREPO":/out -- \
	"sh /d/libbatman-wrappers/build.sh /out"

"$DROIDIAN_DIR/image/build.sh"
"$DROIDIAN_DIR/image/pack-odin.sh"
