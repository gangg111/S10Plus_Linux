#!/bin/bash
# Rebuilds archive packages that still depend on qt6-base-private-abi of a Qt the archive
# no longer has (checked on 11.10.2026 against snapshot 102 + production, which only
# provide Qt 6.11.2; find-stale.py lists them).  The source is Droidian's own git commit
# the archive binary was built from, unchanged; the version is the archive version plus
# +s10rebuild1, and the binaries link against the current Qt, so they install again.
#
# Git rather than apt-get source: the archive serves a maliit-framework orig tarball
# that does not match its own index.  A binary build (-b) does not need it.
#
# find-stale.py also lists qt6-qpa-hwcomposer-plugin (Qt 6.9.2).  Nothing in the image
# depends on it and the phone runs without it, so it is not rebuilt (its CMake does not
# configure against Qt 6.11 anyway: Qt::CorePrivate not found).
#
# Usage: ./build.sh [package ...]      -> $LOCALREPO/*+s10rebuild1*.deb
set -euo pipefail
. "$(dirname "$0")/../env.sh"

declare -A COMMIT=(
	[qt6-text-input-v3]=4bdaf4f213c0bfb84d7feb7e74e6eb0e85c1cd92          # wanted Qt 6.10.2
	[maliit-framework]=8f64f689bbee7046715bc62042be1e18514723cf           # wanted Qt 6.10.2
)
[ $# -gt 0 ] || set -- qt6-text-input-v3 maliit-framework
mkdir -p "$LOCALREPO"

for pkg in "$@"; do
	commit=${COMMIT[$pkg]:-}
	[ -n "$commit" ] || die "no pinned commit for $pkg, add it to COMMIT in this script"
	W=$WORK/src/rebuild-$pkg
	fetch_at "https://github.com/droidian/$pkg" "$commit" "$W/$pkg"
	rm -f "$W"/*.deb "$W"/*.buildinfo "$W"/*.changes
	log "$pkg at ${commit:0:7}, rebuilt for arm64 against the current Qt"
	in_container "$IMG_ARM64" linux/arm64 -v "$W":/b -- "
$APT_SETUP
apt-get install -y -qq --no-install-recommends devscripts equivs >/dev/null
cd /b/$pkg
ver=\$(apt-cache policy $pkg | awk '/Candidate:/ {print \$2}')
[ -n \"\$ver\" ] && [ \"\$ver\" != '(none)' ] || { echo 'no archive version of $pkg'; exit 1; }
# Droidian's packaging repositories carry no debian/changelog (their release tooling
# writes it), so it is created here with the archive version plus +s10rebuild1.
src=\$(sed -n 's/^Source: *//p' debian/control | head -1)
rm -f debian/changelog
DEBEMAIL=build@localhost DEBFULLNAME='S10+ build' \
	dch --create --package \"\$src\" -v \"\$ver+s10rebuild1\" -D rolling --force-distribution \
	'Rebuild of Droidian commit ${commit:0:7} against the Qt of the current archive.'
mk-build-deps -i -r -t 'apt-get -y -qq --no-install-recommends' debian/control >/dev/null
rm -f ${pkg}-build-deps_*
dpkg-buildpackage -b -us -uc -j$JOBS
"
	for d in "$W"/*.deb; do
		case "$d" in *-dbgsym_*|*-build-deps_*) continue;; esac
		cp "$d" "$LOCALREPO"/
		echo "  -> $(basename "$d")"
	done
done
