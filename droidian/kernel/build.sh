#!/bin/bash
# Kernel packages of the port (linux-image, linux-bootimage, linux-headers): the
# LineageOS kernel at a pinned commit plus kernel/patches, cross-built on amd64 in the
# Droidian build-essential container, like the kernel running on the phone.
#
# The ABOX audio firmware is built into the kernel (the DSP asks for it before /vendor is
# mounted).  It is Samsung's and not in this repository: copy the four files from
# /vendor/firmware of your phone (stock Android or the vendor partition) into a directory
# and pass it as ABOX_FIRMWARE.
#
# Usage: ABOX_FIRMWARE=/path/to/abox-fw ./build.sh     -> $LOCALREPO/linux-*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"
: "${ABOX_FIRMWARE:?set ABOX_FIRMWARE to the directory with calliope_sram.bin, calliope_sram_2.bin, calliope_dram.bin and calliope_dram_2.bin}"

K=$WORK/kernel/beyond2lte
log "LineageOS kernel at ${KERNEL_BASE:0:12}"
fetch_at "$KERNEL_REPO" "$KERNEL_BASE" "$K"
log "applying $(ls "$DROIDIAN_DIR"/kernel/patches/*.patch | wc -l) patches"
apply_series "$K" "$DROIDIAN_DIR"/kernel/patches/*.patch

for f in calliope_sram.bin calliope_sram_2.bin calliope_dram.bin calliope_dram_2.bin; do
	[ -f "$ABOX_FIRMWARE/$f" ] || die "missing $ABOX_FIRMWARE/$f"
	cp "$ABOX_FIRMWARE/$f" "$K/firmware/$f"
done

# debian/ is git-ignored in the kernel tree apart from the tracked files, so the changelog
# is written here, with the version scheme of the Droidian kernel packages.
ver="0.0.0+git$(git -C "$K" log -1 --format=%cd --date=format:%Y%m%d%H%M%S).$(git -C "$K" rev-parse --short=7 HEAD).droidian"
cat > "$K/debian/changelog" <<EOF
linux-android-samsung-beyond2lte ($ver) trixie; urgency=medium

  * Galaxy S10+ port kernel, LineageOS ${KERNEL_BASE:0:12} plus droidian/kernel/patches.

 -- S10+ build <build@localhost>  $(LC_ALL=C date -R)
EOF

log "building (cross, aarch64), about 15 to 40 minutes"
rm -f "$WORK"/kernel/linux-*.deb
# The defconfig reads the ABOX firmware from /k/firmware, so the tree is mounted there too.
in_container "$IMG_AMD64" linux/amd64 -v "$WORK/kernel":/buildd -v "$K":/k -w /buildd/beyond2lte -- "
dpkg --add-architecture arm64
$APT_SETUP
apt-get install -y -qq --no-install-recommends linux-packaging-snippets devscripts equivs >/dev/null
# debian/control comes from the linux-packaging-snippets template and kernel-info.mk;
# the build dependencies (clang-android, mkbootimg, avbtool, ...) are taken from it
debian/rules debian/control
mk-build-deps -i -r -t 'apt-get -y -qq --no-install-recommends' debian/control >/dev/null
rm -f linux-android-samsung-beyond2lte-build-deps_*
dpkg-buildpackage -aarm64 -b -us -uc -d -j\$(nproc)
"

mkdir -p "$LOCALREPO"
cp "$WORK"/kernel/linux-*.deb "$LOCALREPO"/
log "done: $(ls "$WORK"/kernel/linux-*.deb | wc -l) packages copied to $LOCALREPO"
