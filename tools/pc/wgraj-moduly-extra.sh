#!/bin/sh
# Wgrywa na telefon moduly z /home/pm/ko-extra (tools/pc/buduj-moduly-extra.sh)
# do /lib/modules/<wersja>/extra, z kopia poprzednich i kontrola sumy odczytem
# z pominieciem pamieci podrecznej (zapis przed resetem sysrq ginie bez fsync).
#
# Uzycie: KLUCZ=<plik> sh tools/pc/wgraj-moduly-extra.sh [adres]
# Kod:    0 wgrane i zgodne, 1 rozjazd sum, 2 brak polaczenia
set -eu
ADRES=${1:-172.16.42.1}
SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 ${KLUCZ:+-i $KLUCZ}"
ZRODLO=${ZRODLO:-//wsl.localhost/Debian/home/pm/ko-extra}
$SSH "user@$ADRES" "uname -r" || exit 2
$SSH "user@$ADRES" "mkdir -p ~/narz/ko-extra"
for m in "$ZRODLO"/*.ko "$ZRODLO"/modules.builtin "$ZRODLO"/modules.builtin.modinfo; do
	$SSH "user@$ADRES" "cat > ~/narz/ko-extra/$(basename "$m")" < "$m"
done
$SSH "user@$ADRES" 'TOK_RAW=1 sh -s' <<'ZDALNIE'
set -eu
M=/lib/modules/$(uname -r)/extra
K=/home/user/narz/ko-extra-poprzednie
rm -rf "$K"; mkdir -p "$K"; cp $M/*.ko "$K/" 2>/dev/null || true
zle=0
for m in /home/user/narz/ko-extra/*.ko; do
	b=$(basename "$m")
	sudo install -m644 "$m" "$M/$b"
	sudo sync "$M/$b"
	a=$(sha256sum "$m" | cut -c1-16)
	d=$(sudo dd if="$M/$b" iflag=direct bs=1M status=none | sha256sum | cut -c1-16)
	printf '  %-18s %s %s\n' "$b" "$a" "$([ "$a" = "$d" ] && echo zgodne || echo ROZJAZD)"
	[ "$a" = "$d" ] || zle=1
done
# listy wbudowanych: z nich depmod robi modules.builtin.bin dla modprobe
for f in modules.builtin modules.builtin.modinfo; do
	sudo install -m644 /home/user/narz/ko-extra/$f /lib/modules/$(uname -r)/$f
done
sudo depmod -a 2>/dev/null
sudo sync /lib/modules/$(uname -r)/modules.dep /lib/modules/$(uname -r)/modules.builtin.bin
exit $zle
ZDALNIE
