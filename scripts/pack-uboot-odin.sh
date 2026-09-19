#!/bin/sh
# Pakowanie zbudowanego U-Boota w obraz rozruchowy i w kontener Odina.
#
# Po co skrypt, a nie recznie. Kazda zmiana w bootloaderze wymaga przejscia tej
# samej sciezki, a kazdy jej etap ma swoja pulapke:
#
#   1. mkbootimg      naglowek v1 i strona 2048 B, bo tego chce S-BOOT tego
#                     telefonu; adres bazowy zostaje domyslny, bo pakiet
#                     postmarketOS dla beyond2lte zadnego nie podaje.
#   2. SEANDROIDENFORCE   S-BOOT odmawia uruchomienia obrazu bez tego ogona.
#                     Doklejany PO mkbootimg, wiec nie jest czescia zadnej
#                     strony i nie liczy sie do rozmiarow z naglowka.
#   3. tar            Odin czyta WYLACZNIE format ustar, a `tar` GNU domyslnie
#                     robi gnu. Stad jawne --format=ustar. Plik w srodku MUSI
#                     nazywac sie boot.img, bo po tej nazwie Odin rozpoznaje,
#                     do ktorej partycji wgrac.
#   4. .md5           nazwa myli: to nie jest plik z suma, tylko sam tar,
#                     do ktorego DOPISANO na koncu sume i nazwe. Odin liczy
#                     sume z tresci przed ta linia.
#
# Uzycie:  scripts/pack-uboot-odin.sh [u-boot.bin] [katalog wyjsciowy]
# Kod:     0 spakowane, 2 brak wejscia albo narzedzi
set -eu

UB=${UBOOT_TREE:-$HOME/u-boot-upstream}
BIN=${1:-$UB/u-boot.bin}
OUT=${2:-/mnt/d/S10Plus-pmos}

command -v mkbootimg >/dev/null 2>&1 || {
	echo "pack-uboot-odin: brak mkbootimg (apt install android-sdk-libsparse-utils mkbootimg)"
	exit 2
}
[ -f "$BIN" ] || { echo "pack-uboot-odin: brak $BIN"; exit 2; }
[ -d "$OUT" ] || { echo "pack-uboot-odin: brak katalogu $OUT"; exit 2; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Parametry z pakietu postmarketOS dla beyond2lte; naglowek v1, bo tego uzywa
# stockowy obraz tego telefonu.
mkbootimg -o "$tmp/boot.img" \
	--kernel		"$BIN" \
	--header_version	1 \
	--pagesize		2048 \
	--kernel_offset		0x00008000 \
	--ramdisk_offset	0x01000000 \
	--second_offset		0xf0000000 \
	--tags_offset		0x00000100 \
	--os_version		12.0.0 \
	--os_patch_level	2021-12

printf 'SEANDROIDENFORCE' >> "$tmp/boot.img"

cp "$tmp/boot.img" "$OUT/boot-uboot-nasz.img"

# Kontener Odina. Sume liczy sie z gotowego tara, a potem dopisuje do niego,
# dokladnie tak jak robi to oficjalne narzedzie Samsunga.
( cd "$tmp" && tar --format=ustar -cf uboot-nasz.tar boot.img )
( cd "$tmp" && md5sum -t uboot-nasz.tar >> uboot-nasz.tar && mv uboot-nasz.tar uboot-nasz.tar.md5 )
cp "$tmp/uboot-nasz.tar.md5" "$OUT/uboot-nasz.tar.md5"

echo "pack-uboot-odin: $BIN -> $OUT"
echo "  u-boot.bin              $(stat -c %s "$BIN") B"
echo "  boot-uboot-nasz.img     $(stat -c %s "$OUT/boot-uboot-nasz.img") B"
echo "  uboot-nasz.tar.md5      $(stat -c %s "$OUT/uboot-nasz.tar.md5") B"
