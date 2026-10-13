#!/bin/sh
# Builds the empty libbatman-wrappers placeholder (no compiler needed).
# Usage: sh build.sh <output dir>   ->  <output dir>/libbatman-wrappers_0.0-s10plus1_all.deb
set -e
here=$(cd "$(dirname "$0")" && pwd)
out=${1:-.}
work=$(mktemp -d)
mkdir -p "$work/DEBIAN" "$work/usr/share/doc/libbatman-wrappers"
cp "$here/control" "$work/DEBIAN/control"
printf 'Empty placeholder for the Galaxy S10+ port, see the package description.\n' \
	> "$work/usr/share/doc/libbatman-wrappers/README"
chmod -R u=rwX,go=rX "$work"
dpkg-deb --root-owner-group --build "$work" "$out/libbatman-wrappers_0.0-s10plus1_all.deb"
rm -rf "$work"
