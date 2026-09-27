#!/bin/sh
# Pakowanie obrazu postmarketOS w kontener Odina, do wgrania na userdata.
#
# Po co skrypt, a nie recznie. Kontener Odina ma trzy wlasciwosci, z ktorych
# kazda po cichu decyduje o powodzeniu:
#
#   1. nazwa pliku W SRODKU archiwum wybiera partycje. `userdata.img` trafia na
#      userdata; ta sama zawartosc pod inna nazwa trafi gdzie indziej albo
#      nigdzie. Nazwa pliku archiwum nie znaczy nic.
#   2. Odin czyta WYLACZNIE format ustar, a `tar` GNU domyslnie robi gnu.
#   3. rozszerzenie .md5 myli: to nie jest plik z suma, tylko sam tar,
#      do ktorego DOPISANO na koncu sume i nazwe. Odin liczy sume z tresci
#      przed ta linia.
#
# Obraz jest kompletnym dyskiem z wlasna tablica GPT o sektorze 4096, wiec po
# zapisie na userdata bootloader widzi go jako zagniezdzony dysk i znajduje
# w nim partycje systemowa EFI. Tak wlasnie ma dzialac: kod plyty buduje mape
# na najwiekszej partycji i oddaje ja jako urzadzenie blokowe.
#
# UWAGA: wgranie tego kasuje dane Androida na userdata. Partycji warstwy
# pierwszej (efs, IMEI, klucze) nie dotyka.
#
# Uzycie:  scripts/pack-pmos-odin.sh [obraz] [katalog wyjsciowy] [rdzen nazwy]
# Kod:     0 spakowane, 2 brak wejscia albo narzedzi
set -eu

OUT_DEFAULT=/mnt/d/S10Plus-pmos
IMG=${1:-$OUT_DEFAULT/pmos-nasza-seria.img}
OUT=${2:-$OUT_DEFAULT}
RDZEN=${3:-pmos-userdata}

[ -f "$IMG" ] || { echo "pack-pmos-odin: brak $IMG" >&2; exit 2; }
[ -d "$OUT" ] || { echo "pack-pmos-odin: brak katalogu $OUT" >&2; exit 2; }
command -v md5sum >/dev/null 2>&1 || {
	echo "pack-pmos-odin: brak md5sum" >&2; exit 2; }

# Partycja userdata przyjmuje obraz w formacie sparse, nie surowy. Surowy
# przechodzi WSZYSTKIE sprawdzenia po stronie PC: suma sie zgadza, Odin melduje
# "Checking MD5 finished Sucessfully", odczytuje tablice partycji i zaczyna
# zapis. Dopiero telefon staje w polowie, bez jednej linii bledu, i wymaga
# recznego restartu. Znany tryb awarii, Heimdall #453.
#
# Dlatego ladunek jest sprawdzany TUTAJ, a nie na telefonie.
MAGIA=$(od -An -tx1 -N4 "$IMG" | tr -d ' \n')
if [ "$MAGIA" != "3aff26ed" ] && [ "${POZWOL_SUROWY:-0}" != "1" ]; then
	echo "pack-pmos-odin: $IMG nie jest obrazem sparse (pierwsze bajty" \
	     "$MAGIA, oczekiwane 3aff26ed)." >&2
	echo "  Przepusc go przez: img2simg $IMG <wynik> 4096" >&2
	echo "  Swiadomie surowy: POZWOL_SUROWY=1 $0 ..." >&2
	exit 2
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Twardy link zamiast kopii: obraz ma ponad gigabajt, a tar i tak czyta tresc.
ln "$IMG" "$tmp/userdata.img" 2>/dev/null || cp "$IMG" "$tmp/userdata.img"

# Nazwa archiwum MUSI byc nazwa koncowa bez .md5, bo md5sum zapisuje ja w
# dopisywanej linii, a Odin porownuje jedna z druga. Zbudowane pod nazwa
# tymczasowa archiwum przechodzi wszystkie wlasne sprawdzenia i dopiero
# telefon odmawia: "md5 error! Binary is invalid".
NAZWA=$RDZEN.tar

( cd "$tmp" && tar --format=ustar -cf "$NAZWA" userdata.img )
( cd "$tmp" && md5sum -t "$NAZWA" >> "$NAZWA" && mv "$NAZWA" "$NAZWA.md5" )
mv "$tmp/$NAZWA.md5" "$OUT/$NAZWA.md5"

# Bramka, zeby ten blad nie wrocil: nazwa w linii sumy kontra nazwa pliku.
LINIA=$(tail -c 120 "$OUT/$NAZWA.md5" | tr -d '\0' | tail -1)
W_SUMIE=$(printf '%s' "$LINIA" | sed 's/^[0-9a-f]*  *//')
if [ "$W_SUMIE" != "$NAZWA" ]; then
	echo "pack-pmos-odin: linia sumy mowi o $W_SUMIE, a plik nazywa sie" \
	     "$NAZWA, Odin to odrzuci" >&2
	exit 2
fi

echo "pack-pmos-odin: $IMG -> $OUT"
echo "  obraz                   $(stat -c %s "$IMG") B"
echo "  $NAZWA.md5   $(stat -c %s "$OUT/$NAZWA.md5") B"
echo "  plik w srodku           $(tar -tf "$OUT/$NAZWA.md5" 2>/dev/null | head -1)"
echo "  nazwa w linii sumy      $W_SUMIE"
