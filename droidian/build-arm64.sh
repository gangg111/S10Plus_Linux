#!/bin/bash
# Builds a Debian source tree for arm64 inside the Droidian build-essential container and
# copies the binary packages (without -dbgsym) into the local repository.  On a PC the
# container runs emulated (qemu-user through binfmt, see README), so a big package takes
# tens of minutes; on an arm64 machine it runs natively.
#
# Usage: ./build-arm64.sh <source dir>
set -euo pipefail
. "$(dirname "$0")/env.sh"
src=$(cd "${1:?usage: build-arm64.sh <source dir>}" && pwd)
parent=$(dirname "$src")
name=$(basename "$src")
mkdir -p "$LOCALREPO"
[ -f "$LOCALREPO/Packages" ] || : > "$LOCALREPO/Packages"

log "building $name for arm64"
in_container "$IMG_ARM64" linux/arm64 -v "$parent":/b -v "$LOCALREPO":/localrepo -- "
$APT_SETUP
apt-get install -y -qq --no-install-recommends devscripts equivs >/dev/null
cd /b/$name
mk-build-deps -i -r -t 'apt-get -y -qq --no-install-recommends' debian/control >/dev/null
rm -f ../*.deb
dpkg-buildpackage -b -us -uc -j$JOBS
"
for d in "$parent"/*.deb; do
	case "$d" in *-dbgsym_*|*-build-deps_*) continue;; esac
	cp "$d" "$LOCALREPO"/
	echo "  -> $(basename "$d")"
done
