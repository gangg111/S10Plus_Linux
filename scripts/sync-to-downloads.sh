#!/bin/sh
# Kopiuje projekt (bez sources/ - te odtwarza fetch-sources.sh) do /sdcard/Download.
# Uruchamiane po kazdej implementacji.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dst=${1:-/sdcard/Download/s10-mainline}

mkdir -p "$dst"
rsync -a --delete --exclude 'sources/' --exclude '.git/' "$root"/ "$dst"/

# migawka historii gita bez samego .git (zeby dalo sie ja czytac na telefonie)
git -C "$root" log --oneline --stat > "$dst/GIT-LOG.txt" 2>/dev/null || true

echo "OK: $(du -sh "$dst" | cut -f1) w $dst"
