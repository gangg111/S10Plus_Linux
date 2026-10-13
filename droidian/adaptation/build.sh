#!/bin/bash
# The device adaptation (tools/phone/adaptacja): adaptation-samsung-beyond2lte,
# -configs and -tools.  -tools ships prebuilt binaries whose sources are in this
# repository; tools/phone/adaptacja/README.md lists each one with its checksum.
#
# Usage: ./build.sh      -> $LOCALREPO/adaptation-samsung-beyond2lte*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"

S=$WORK/src/adaptacja
rm -rf "$S"; mkdir -p "$(dirname "$S")"
cp -r "$REPO_DIR/tools/phone/adaptacja" "$S"
# modes from scratch (a Windows checkout has none or all bits), as buduj.sh does
find "$S" -type f -exec chmod 0644 {} +
chmod +x "$S"/debian/rules "$S"/debian/*.preinst "$S"/debian/*.postinst "$S"/debian/*.postrm \
	"$S"/usr/lib/s10plus/* "$S"/tools/maliit/maliit-keyboard
"$DROIDIAN_DIR/build-arm64.sh" "$S"
