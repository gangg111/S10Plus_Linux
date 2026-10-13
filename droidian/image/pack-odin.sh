#!/bin/bash
# Packs the debos output for Odin, the same way as the files on the Releases page:
#   droidian-boot-s10plus.tar.md5      boot.img           -> flashes to boot
#   droidian-userdata.tar.md5          userdata.img       -> flashes to userdata
# Both go through the AP slot, one after the other (main README, "Install with Odin").
# Odin picks the partition by the file name inside the tar, and checks the md5 line
# appended at the end, which has to carry the name of the .tar.md5 itself.
#
# Usage: ./pack-odin.sh [image zip]      -> $WORK/odin/*.tar.md5
set -euo pipefail
. "$(dirname "$0")/../env.sh"
zip=${1:-$(ls -t "$WORK"/images/out/*.zip 2>/dev/null | head -1)}
[ -f "$zip" ] || die "no image zip, run image/build.sh first"

O=$WORK/odin
rm -rf "$O"; mkdir -p "$O/x"
log "unpacking $(basename "$zip")"
unzip -q -o "$zip" data/boot.img data/userdata.img -d "$O/x"

odin_tar() { # <file inside> <name.tar.md5>
	local inner=$1 out=$2
	(cd "$O/x/data" && tar --format=ustar -cf "$O/${out%.md5}" "$inner")
	(cd "$O" && md5sum -t "${out%.md5}" >> "${out%.md5}" && mv "${out%.md5}" "$out")
	echo "  $out: $(stat -c %s "$O/$out") B, contains $(tar -tf "$O/$out" 2>/dev/null | head -1)"
}
odin_tar boot.img droidian-boot-s10plus.tar.md5
odin_tar userdata.img droidian-userdata.tar.md5
rm -rf "$O/x"
log "ready in $O (flash as described in the main README)"
