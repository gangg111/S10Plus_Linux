# Shared settings and helpers for the Droidian build scripts.  Source it, do not run it.
# shellcheck shell=bash

# The Droidian archive the port was built and tested against (snapshot 102 plus the
# rolling production repository, Qt 6.11.2).
DROIDIAN_SOURCES='deb http://releases.droidian.org/snapshots/102 rolling main
deb https://production.repo.droidian.org trixie main'

IMG_AMD64=quay.io/droidian/build-essential:next-amd64
IMG_ARM64=quay.io/droidian/build-essential:next-arm64
IMG_ROOTFS=quay.io/droidian/rootfs-builder:next-amd64

# Upstream commits the patch series apply to.  Pinned on purpose: the series are
# tested against exactly these trees, whatever the branches look like later.
KERNEL_REPO=https://github.com/LineageOS/android_kernel_samsung_exynos9820
KERNEL_BASE=a412cfaf86b980ce35cae96a35f678c8ea551575      # lineage-23.2
SHELL_REPO=https://github.com/droidian/plasma-mobile-wf
SHELL_BASE=91ba13c86f6893fed1505acf97c5594a67318ab3       # group/next/plasma-6.5
CAMERA_REPO=https://github.com/droidian/droidian-camera
CAMERA_BASE=7071899974c08a2b59ce394db24911a1aaeabd19      # feature/next/hybris-compat
SETTINGS_REPO=https://invent.kde.org/plasma-mobile/plasma-settings.git
SETTINGS_BASE=e6b962710aef6adae969176a111dab0e54cccb46    # v26.04.0
IMAGES_REPO=https://github.com/droidian-images/droidian
IMAGES_BASE=b1fe26b4da12227094a19b7665b63cfa5e7dd2c0
TEMPLATES_REPO=https://github.com/droidian-releng/rootfs-templates
TEMPLATES_BASE=d2212f43e8de78e3b759d94ee427e24268655aee

DROIDIAN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$DROIDIAN_DIR/.." && pwd)
WORK=${WORK:-$HOME/s10plus-build}
LOCALREPO=${LOCALREPO:-$WORK/localrepo}

# Parallel jobs for the arm64 builds under emulation.  A C++ job with LTO under qemu
# takes well over a gigabyte, and 24 jobs in 15 GB took the whole WSL VM down, so the
# count follows the memory (about 2 GB per job), not the cores.  Override with JOBS=n.
if [ -z "${JOBS:-}" ]; then
	JOBS=$(( $(awk '/MemTotal/ {print int($2 / 1048576)}' /proc/meminfo) / 2 ))
	[ "$JOBS" -ge 1 ] || JOBS=1
	[ "$JOBS" -le "$(nproc)" ] || JOBS=$(nproc)
fi

log() { printf '\n=== %s ===\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# fetch_at <url> <commit> <dir>: a clean checkout of exactly <commit> (no history needed)
fetch_at() {
	local url=$1 commit=$2 dir=$3
	if [ -d "$dir/.git" ] && [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" = "$commit" ] &&
	   git -C "$dir" reset -q --hard && git -C "$dir" clean -qfdx 2>/dev/null; then
		return
	fi
	# a container build that was killed leaves root-owned files behind
	rm -rf "$dir" 2>/dev/null || die "cannot remove $dir (files left by an interrupted container build belong to root): sudo rm -rf '$dir'"
	git init -q "$dir"
	git -C "$dir" remote add origin "$url"
	git -C "$dir" fetch -q --depth 1 origin "$commit"
	git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD
}

# apply_series <dir> <patch...>: git am with a neutral committer, author kept from the patches
apply_series() {
	local dir=$1; shift
	git -C "$dir" -c user.name="S10+ build" -c user.email="build@localhost" am -q "$@" \
		|| die "the series did not apply in $dir (see git am output above)"
}

# in_container <image> <platform> <mounts...> -- <script>: run a script in a Droidian build container
in_container() {
	local image=$1 platform=$2; shift 2
	local mounts=()
	while [ "$1" != "--" ]; do mounts+=("$1"); shift; done
	shift
	# the build runs as root in the container; whatever it wrote in the mounted
	# directories is handed back to the caller, so a second run can clean it up
	docker run --rm --platform "$platform" "${mounts[@]}" -e DROIDIAN_SOURCES="$DROIDIAN_SOURCES" \
		-e OWNER="$(id -u):$(id -g)" "$image" bash -euo pipefail -c "
trap 'chown -R \"\$OWNER\" /b /buildd /k /out /localrepo 2>/dev/null || true' EXIT
$1"
}

# shell snippet run first in every build container: our archive, plus the local repo if present
APT_SETUP='printf "%s\n" "$DROIDIAN_SOURCES" > /etc/apt/sources.list
if [ -f /localrepo/Packages ]; then
	echo "deb [trusted=yes] file:/localrepo ./" > /etc/apt/sources.list.d/zz-local.list
fi
apt-get update -qq'
