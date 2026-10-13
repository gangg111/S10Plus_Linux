#!/bin/sh
# Builds the One UI QML overlays of the -tools package from the archive's own files.
#
# qml-oneui.diff changes 12 files of three archive packages (kirigami-addons FormCard,
# Kirigami controls, the Breeze Qt Quick style).  Copying our edited files over a newer
# release would mix two versions in one QML module, so instead the packages are fetched
# from the archive here, the diff is applied to exactly their files, and -tools depends
# on exactly those versions.  If a later release moves the code, the patch fails and the
# build stops; nothing broken gets packaged.
#
# Usage (from debian/rules): sh qml-oneui.sh <output dir> <substvars file>
set -eu
out=$1
substvars=$2
here=$(cd "$(dirname "$0")" && pwd)
PKGS="qml6-module-org-kde-kirigamiaddons-formcard qml6-module-org-kde-kirigami qml6-module-org-kde-breeze"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/debs" "$tmp/root"
(cd "$tmp/debs" && apt-get download $PKGS)

deps=""
for p in $PKGS; do
	deb=$(ls "$tmp"/debs/"${p}"_*.deb)
	dpkg-deb -x "$deb" "$tmp/root"
	deps="${deps:+$deps, }$p (= $(dpkg-deb -f "$deb" Version))"
done

patch -d "$tmp/root" -p1 --no-backup-if-mismatch -F0 < "$here/qml-oneui.diff"

rm -rf "$out"
sed -n 's|^+++ b/||p' "$here/qml-oneui.diff" | while read -r f; do
	mkdir -p "$out/$(dirname "$f")"
	cp "$tmp/root/$f" "$out/$f"
done
echo "oneui:Depends=$deps" >> "$substvars"
echo "qml-oneui: $deps"
