#!/bin/bash
# The Droidian image of the port (Plasma Mobile on wayfire, API 32) with debos, from the
# local repository the package scripts filled.  droidian-images and rootfs-templates are
# taken at pinned commits; image/0001-*.patch adds the local repository, pinned to 1100
# (above Droidian's own 1002) before the first package is installed, so the port packages
# win over the archive.
#
# Needs a kernel with loop and device-mapper (the WSL2 kernel has both), Docker, and
# arm64 emulation (README.md, step 1).  Takes about an hour on a PC.
#
# Usage: ./build.sh      -> $WORK/images/out/droidian-*.zip
set -euo pipefail
. "$(dirname "$0")/../env.sh"
[ -n "$(ls "$LOCALREPO"/*.deb 2>/dev/null)" ] || die "the local repository $LOCALREPO is empty, build the packages first"

I=$WORK/images
log "droidian-images at ${IMAGES_BASE:0:12}"
fetch_at "$IMAGES_REPO" "$IMAGES_BASE" "$I"
git -C "$I" submodule update -q --init --depth 1
[ "$(git -C "$I/rootfs-templates" rev-parse HEAD)" = "$TEMPLATES_BASE" ] \
	|| die "rootfs-templates is not at $TEMPLATES_BASE"
apply_series "$I/rootfs-templates" "$DROIDIAN_DIR"/image/*.patch
cp "$DROIDIAN_DIR/image/community_devices.yml" "$I/"
rm -rf "$I/localrepo"
cp -r "$LOCALREPO" "$I/localrepo"
mkdir -p "$I/out"

log "debos"
# --privileged and the cgroup mount for systemd inside the builder; /dev as /host-dev
# because genimage.sh finds the LVM volumes there.
in_container "$IMG_ROOTFS" linux/amd64 --privileged --cgroupns=host \
	-v /sys/fs/cgroup:/sys/fs/cgroup:rw -v /dev:/host-dev \
	-v "$I":/buildd/sources -w /buildd/sources -- "
python3 -c 'import yaml' 2>/dev/null || { apt-get update -qq && apt-get install -y -qq python3-yaml >/dev/null; }
(cd localrepo && dpkg-scanpackages -m . > Packages 2>/dev/null)
DROIDIAN_VERSION=102 python3 generate_device_recipe.py samsung_beyond2lte arm64 plamo_wf_experimental phone 32
debos --disable-fakemachine generated/droidian.yaml
"
ls -la "$I"/out/*.zip
