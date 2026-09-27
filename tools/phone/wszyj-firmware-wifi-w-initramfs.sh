#!/bin/sh
# Wklada firmware Wi-Fi do initramfs, zeby wbudowany brcmfmac znalazl je
# przy starcie jadra.
#
# Po co to istnieje.  Sterownik kontrolera PCIe i brcmfmac sa wbudowane,
# wiec lacze wstaje, a brcmfmac prosi o firmware, zanim zamontuje sie
# docelowy korzen z /lib/firmware.  Loader firmware czeka tylko na initramfs
# (wait_for_initramfs), a pomocnika w przestrzeni uzytkownika jadro nie ma,
# wiec bez tych plikow w initramfs sonda urzadzenia konczy sie bledem
# i wlan0 nie powstaje.  Zmierzone 23.09.2026: ten sam sterownik zaladowany
# pozniej (insmod po starcie) wgral firmware i dal wlan0.
#
# Jakie pliki.  Trzy, pod nazwami, ktorych szuka brcmfmac dla BCM4375:
#   brcmfmac4375-pcie.bin       obraz producenta bcmdhd_sta.bin_b1
#   brcmfmac4375-pcie.txt       NVRAM modulu, dla B1 Semco nvram.txt_CS01_semco_b1
#   brcmfmac4375-pcie.clm_blob  tablica regulacyjna bcmdhd_clm.blob
# Pliki naleza do producenta i nie leza w repo; bierze sie je z telefonu
# (tools/bt/firmware-lacznosci.sh kladzie je w /lib/firmware/brcm).
#
# Uzycie:
#   FIRMWARE=<katalog z trzema plikami> \
#     tools/phone/wszyj-firmware-wifi-w-initramfs.sh <initramfs we> <initramfs wy>
#
# Wymaga roota (cpio odtwarza wlascicieli i urzadzenia) oraz zstd i cpio.
set -eu
WE=${1:?podaj plik initramfs wejsciowy}
WY=${2:?podaj plik initramfs wyjsciowy}
FIRMWARE=${FIRMWARE:?ustaw FIRMWARE na katalog z plikami brcmfmac4375-pcie.*}

PLIKI="brcmfmac4375-pcie.bin brcmfmac4375-pcie.txt brcmfmac4375-pcie.clm_blob"
for n in zstd cpio; do
	command -v "$n" >/dev/null || { echo "brak narzedzia $n" >&2; exit 1; }
done
for p in $PLIKI; do
	[ -s "$FIRMWARE/$p" ] || { echo "brak albo pusty $FIRMWARE/$p" >&2; exit 1; }
done
# NVRAM musi byc od rewizji B1, bo obraz jest tylko w wersji _b1; wariant
# b0 lezal tu kiedys przez pomylke, bo skrypt bral pierwszy z brzegu.
head -1 "$FIRMWARE/brcmfmac4375-pcie.txt" | grep -q 'B1' || {
	echo "NVRAM nie jest od rewizji B1: $(head -1 "$FIRMWARE/brcmfmac4375-pcie.txt")" >&2
	exit 1
}

PRACA=$(mktemp -d)
trap 'rm -rf "$PRACA"' EXIT
KORZEN="$PRACA/korzen"
mkdir -p "$KORZEN"

echo "== rozpakowanie =="
zstd -d -q -f "$WE" -o "$PRACA/wejscie.cpio"
( cd "$KORZEN" && cpio -idm --quiet < "$PRACA/wejscie.cpio" )
[ -d "$KORZEN/hooks-cleanup" ] || {
	echo "ten initramfs nie ma katalogu /hooks-cleanup, to nie jest pmOS" >&2
	exit 1
}

echo "== ladunek =="
install -d -m 0755 "$KORZEN/lib/firmware/brcm"
for p in $PLIKI; do
	install -m 0644 "$FIRMWARE/$p" "$KORZEN/lib/firmware/brcm/$p"
done

# Staly czas na calym drzewie, z tego samego powodu co w
# wszyj-klawiature-w-initramfs.sh: bez tego dwa przebiegi roznia sie
# czasem rozpakowania katalogow.
find "$KORZEN" -exec touch -h -d @0 {} +

echo "== spakowanie =="
( cd "$KORZEN" && find . -print0 | LC_ALL=C sort -z |
	cpio --create --format=newc --reproducible --quiet --null ) \
	> "$PRACA/wyjscie.cpio"
zstd -q -f -19 "$PRACA/wyjscie.cpio" -o "$WY"

echo "== audyt =="
SPR="$PRACA/sprawdz"
mkdir -p "$SPR"
zstd -d -q -f "$WY" -o "$PRACA/sprawdz.cpio"
( cd "$SPR" && cpio -idm --quiet < "$PRACA/sprawdz.cpio" )
zle=0
for p in $PLIKI; do
	if cmp -s "$FIRMWARE/$p" "$SPR/lib/firmware/brcm/$p"; then
		echo "  ok   lib/firmware/brcm/$p"
	else
		echo "  ZLE  lib/firmware/brcm/$p"; zle=$((zle + 1))
	fi
done
for p in init init_2nd.sh init_functions.sh hooks-cleanup; do
	[ -e "$SPR/$p" ] && echo "  ok   $p" || { echo "  BRAK $p"; zle=$((zle + 1)); }
done
ls -l "$WE" "$WY" | awk '{printf "  %-52s %s B\n", $NF, $5}'
[ "$zle" = 0 ] || { echo "audyt: $zle bledow, NIE uzywaj tego pliku" >&2; exit 1; }
echo "audyt czysty"
