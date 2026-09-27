#!/bin/sh
# Podmienia jadro i drzewo urzadzen w obrazie pmOS, nie ruszajac reszty.
#
# Po co osobny skrypt. Obraz niesie takze rzeczy wstrzykniete wczesniej:
# usluge firmware lacznosci, regule sudo bez hasla i filtr tok razem
# z kluczami. Przebudowa obrazu od zera kasowalaby je za kazdym razem;
# ten skrypt dotyka wylacznie dwoch plikow na partycji rozruchowej.
#
# Uruchamiac jako root w WSL, bo montuje obraz przez urzadzenie petlowe.
set -e

D=/mnt/d/S10Plus-pmos
L=/home/pm/linux
SUROWY=$D/pmos-nasza-seria.img
BOOT=/mnt/pmos-boot
OFS_BOOT=8388608
LEN_BOOT=503316480

umount "$BOOT" 2>/dev/null || true
losetup -D 2>/dev/null || true
mkdir -p "$BOOT"
P=$(losetup --find --show --offset $OFS_BOOT --sizelimit $LEN_BOOT "$SUROWY")
trap 'umount "$BOOT" 2>/dev/null || true; losetup -d "$P" 2>/dev/null || true' EXIT
mount "$P" "$BOOT"

echo "== co bylo =="
printf '  jadro  %s  %s B\n' \
	"$(sha256sum "$BOOT/vmlinuz-s10" | cut -c1-16)" \
	"$(stat -c %s "$BOOT/vmlinuz-s10")"

install -m 0644 "$L/arch/arm64/boot/Image" "$BOOT/vmlinuz-s10"
install -m 0644 "$L/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb" \
	"$BOOT/dtbs/exynos/exynos9820-beyond2lte.dtb"

echo "== co jest =="
printf '  jadro  %s  %s B\n' \
	"$(sha256sum "$BOOT/vmlinuz-s10" | cut -c1-16)" \
	"$(stat -c %s "$BOOT/vmlinuz-s10")"
printf '  drzewo %s  %s B\n' \
	"$(sha256sum "$BOOT/dtbs/exynos/exynos9820-beyond2lte.dtb" | cut -c1-16)" \
	"$(stat -c %s "$BOOT/dtbs/exynos/exynos9820-beyond2lte.dtb")"

echo
echo "== kontrola, ze reszta wstrzyknietych rzeczy nie znikla =="
ROOT=/mnt/pmos-root
OFS_ROOT=511705088
LEN_ROOT=771751936
mkdir -p "$ROOT"
P2=$(losetup --find --show --offset $OFS_ROOT --sizelimit $LEN_ROOT "$SUROWY")
mount "$P2" "$ROOT"
for f in usr/local/bin/firmware-lacznosci.sh etc/sudoers.d/10-praca-zdalna \
	 home/user/.local/bin/tok home/user/.ssh/authorized_keys; do
	if [ -e "$ROOT/$f" ]; then
		printf '  jest   %s\n' "$f"
	else
		printf '  BRAK   %s\n' "$f"
	fi
done
umount "$ROOT"
losetup -d "$P2"

umount "$BOOT"
losetup -d "$P"
trap - EXIT
echo
echo "obraz zaktualizowany: $SUROWY"
