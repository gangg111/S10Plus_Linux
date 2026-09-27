#!/bin/sh
# Wyjmuje z partycji producenta firmware obu polowek ukladu lacznosci.
#
# Uruchamiane na telefonie, jednym przebiegiem, zeby nie montowac tej partycji
# kilka razy.  Wynik laduje w /tmp, skad komputer zabiera go po sieci.
#
# Bluetooth: plik lat .hcd, ktory host wgrywa przy kazdym starcie; bez niego
# uklad nie ma ani adresu, ani pelnej obslugi.
# Wi-Fi: obraz ukladu i jego kalibracja; sterownik producenta szuka ich pod
# nazwami bcmdhd*.bin i nvram*.txt, mainline'owy brcmfmac pod innymi, wiec
# bierzemy wszystko, co tam jest, i nazwy dobieramy po stronie komputera.
set -u

WYNIK=/tmp/firmware-lacznosci
MNT=/mnt/vendor-ro

rm -rf "$WYNIK"
mkdir -p "$WYNIK"

VENDOR=""
for k in /dev/block/by-name/vendor /dev/disk/by-partlabel/vendor \
         /dev/sda26 /dev/block/sda26; do
	[ -b "$k" ] && { VENDOR=$k; break; }
done

if [ -z "$VENDOR" ]; then
	echo "BLAD: nie znalazlem partycji producenta"
	echo "urzadzenia blokowe:"
	ls /dev/sd* 2>/dev/null
	exit 1
fi
echo "partycja producenta: $VENDOR"

mkdir -p "$MNT"
if ! mount -o ro "$VENDOR" "$MNT" 2>&1; then
	echo "BLAD: nie moge zamontowac $VENDOR"
	exit 1
fi

echo "== co jest w katalogu firmware =="
ls -l "$MNT/firmware" 2>/dev/null | head -40

echo
echo "== kopiowanie =="
for wzor in '*.hcd' 'bcmdhd*' 'nvram*' '*.blob' 'bcm*'; do
	find "$MNT" -iname "$wzor" 2>/dev/null | while read -r f; do
		cp "$f" "$WYNIK/" 2>/dev/null &&
			printf '  %s  %s B\n' "$(basename "$f")" "$(stat -c %s "$f")"
	done
done

umount "$MNT"

echo
echo "== sumy =="
sha256sum "$WYNIK"/* 2>/dev/null | cut -c1-24,65-

echo
echo "gotowe, pliki leza w $WYNIK"
