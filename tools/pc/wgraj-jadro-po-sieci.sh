#!/bin/sh
# Podmienia jadro i drzewo na telefonie po sieci, bez Odina i bez trybu pobierania.
#
# Po co.  Wgranie calego obrazu przez Odina trwa kilka minut, wymaga trzymania
# przyciskow i za kazdym razem czlowieka przy telefonie.  Samo jadro to 44 MB
# i lezy na partycji rozruchowej, ktora dziala telefon ma zamontowana: da sie
# je podmienic przez to samo polaczenie, ktorym i tak czytamy logi.
#
# Warunek: uzytkownik na telefonie musi miec prawo zapisu do /boot, czyli
# regule sudo bez pytania o haslo.  Obraz ja niesie; na systemie wgranym
# wczesniej trzeba ja dodac jeden raz.
#
# Uzycie:  tools/pc/wgraj-jadro-po-sieci.sh [adres]
# Klucz:   KLUCZ=<plik> ; klucz roboczy ma wymuszony filtr tok, wiec pliki
#          ida strumieniem przez powloke, nie przez scp (patrz tools/phone)
# Kod:     0 wgrane i telefon restartuje, 1 blad, 2 brak polaczenia
set -eu

ADRES=${1:-172.16.42.1}
UZYTKOWNIK=user
KLUCZ=${KLUCZ:-}
WSL_JADRO='\\wsl.localhost\Debian\home\pm\linux\arch\arm64\boot'
JADRO=${JADRO:-/mnt/c/../}

root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ZRODLO=${ZRODLO:-//wsl.localhost/Debian/home/pm/linux/arch/arm64/boot}

if [ -n "$KLUCZ" ]; then
	SSH="ssh -i $KLUCZ -o BatchMode=yes -o ConnectTimeout=10"
else
	SSH="ssh -o BatchMode=yes -o ConnectTimeout=10"
fi

echo "== czy telefon odpowiada =="
$SSH "$UZYTKOWNIK@$ADRES" "uname -r" || {
	echo "brak polaczenia z $ADRES" >&2
	exit 2
}

echo
echo "== czy mozna pisac do partycji rozruchowej =="
$SSH "$UZYTKOWNIK@$ADRES" "sudo -n true" 2>/dev/null || {
	echo "uzytkownik nie ma prawa zapisu bez hasla." >&2
	echo "Jeden raz, na telefonie albo stad z haslem:" >&2
	echo "  echo 'user ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/10-praca-zdalna" >&2
	exit 1
}

echo
echo "== wysylanie =="
# Nie scp, tylko strumien przez powloke, i to z dwoch powodow naraz. Ten
# telefon nie ma binarki scp: sshd obsluguje przesylanie wbudowanym
# internal-sftp, a klucz roboczy ma wymuszone polecenie (filtr tok), ktore
# przechwytuje takze zadania podsystemu. Strumien binarny przez filtr
# przechodzi bez zmiany ani jednego bajtu, co zostalo sprawdzone na
# 200 000 losowych bajtow porownaniem sum sha256.
$SSH "$UZYTKOWNIK@$ADRES" "cat > /tmp/Image" < "$ZRODLO/Image"
$SSH "$UZYTKOWNIK@$ADRES" "cat > /tmp/exynos9820-beyond2lte.dtb" \
	< "$ZRODLO/dts/exynos/exynos9820-beyond2lte.dtb"

# Przesylanie bez kontroli sumy to zgadywanie, a plik ma 44 MB i idzie przez
# kabel, ktory w tym projekcie juz raz sie rozlaczal.
for para in "Image:/tmp/Image" \
	    "dts/exynos/exynos9820-beyond2lte.dtb:/tmp/exynos9820-beyond2lte.dtb"; do
	lokalny=$ZRODLO/${para%%:*}
	zdalny=${para##*:}
	tu=$(sha256sum "$lokalny" | cut -d' ' -f1)
	tam=$($SSH "$UZYTKOWNIK@$ADRES" "TOK_RAW=1 sha256sum $zdalny" | cut -d' ' -f1)
	if [ "$tu" != "$tam" ]; then
		echo "suma $zdalny sie nie zgadza, przerywam" >&2
		echo "  tu:  $tu" >&2
		echo "  tam: $tam" >&2
		exit 1
	fi
	echo "  $(basename "$zdalny") $(echo "$tu" | cut -c1-16) zgodne"
done

echo
echo "== podmiana =="
$SSH "$UZYTKOWNIK@$ADRES" "sh -s" <<'KONIEC'
set -eu
# Kopia poprzedniego jadra zostaje obok: gdyby nowe nie wstalo, bootloader
# dostaje drugi wpis, ktorym da sie wrocic bez komputera.
sudo cp -f /boot/vmlinuz-s10 /boot/vmlinuz-s10.poprzednie 2>/dev/null || true
sudo cp -f /boot/dtbs/exynos/exynos9820-beyond2lte.dtb \
	/boot/dtbs/exynos/exynos9820-beyond2lte.dtb.poprzednie 2>/dev/null || true

sudo install -m 0644 /tmp/Image /boot/vmlinuz-s10
sudo install -m 0644 /tmp/exynos9820-beyond2lte.dtb \
	/boot/dtbs/exynos/exynos9820-beyond2lte.dtb
# Samo `sync` tu NIE wystarcza.  /boot to FAT w pliku-petli na /dev/sda31
# z bezposrednim I/O, a `sync` nie wysyla do UFS polecenia oproznienia jego
# pamieci podrecznej.  Zmierzone 24.09.2026: reset przez sysrq kilka sekund
# po wgraniu zostawil na partycji stare jadro i stara kopie, czyli nie
# przetrwal ani jeden zapis.  fsync na pliku FAT przechodzi przez petle
# jako flush az do urzadzenia, dlatego `sync` z nazwami plikow.
sudo sync /boot/vmlinuz-s10 /boot/vmlinuz-s10.poprzednie \
	/boot/dtbs/exynos/exynos9820-beyond2lte.dtb \
	/boot/dtbs/exynos/exynos9820-beyond2lte.dtb.poprzednie
sudo sync -f /boot
sudo sync

# Suma z odczytu z pominieciem pamieci podrecznej stron, porownana z tym,
# co przyszlo.  Suma liczona z RAM pokazalaby nowe jadro takze wtedy, gdy
# na dysku zostalo stare, i tak wlasnie bylo.
for para in /tmp/Image:/boot/vmlinuz-s10 \
	    /tmp/exynos9820-beyond2lte.dtb:/boot/dtbs/exynos/exynos9820-beyond2lte.dtb; do
	z=${para%%:*}
	c=${para##*:}
	a=$(sha256sum < "$z" | cut -c1-64)
	b=$(sudo dd if="$c" bs=1M iflag=direct status=none | sha256sum | cut -c1-64)
	if [ "$a" != "$b" ]; then
		echo "  $c odczytany z dysku rozni sie od wyslanego, restartu nie bedzie" >&2
		exit 1
	fi
	echo "  $(basename "$c") $(echo "$b" | cut -c1-16) zgodne po odczycie z dysku"
done
rm -f /tmp/Image /tmp/exynos9820-beyond2lte.dtb
KONIEC

echo
echo "== restart =="
# Nie przez systemd.  Zmierzone 22.09.2026: `systemctl reboot` potrafi
# stanac na `sd 0:0:0:0: [sda] Synchronizing SCSI cache` i nie ruszyc
# przez pol godziny.  Jadro zyje, userspace jest juz zabity, wiec z
# komputera wyglada to jak zawieszony ROZRUCH, a resetu w ogole nie ma
# i nie ma juz czym go wymusic, bo sshd nie zyje.  Zdarza sie po
# zapisach na partycje, a wiec dokladnie po tym, co robi ten skrypt.
#
# `echo b` idzie przez emergency_restart(), czyli omija
# device_shutdown() razem z tym poleceniem do pamieci masowej.  Dane
# sa juz zsynchronizowane wyzej i przez `echo s`, a ext4 po takim
# resecie wstawal bez odtwarzania dziennika.
# Gadzet USB trzeba odpiac JAWNIE.  Zwykle wylaczanie robi to samo przez
# device_shutdown(), ktory tu wlasnie omijamy, wiec bez tego host widzi
# caly czas to samo urzadzenie, nie zauwaza ponownego podlaczenia i po
# restarcie telefon jest niewidoczny, mimo ze dziala.  Zmierzone: po
# resecie przez sysrq trzeba bylo fizycznie przepiac kabel.
#
# Caly ciag MUSI pojsc jednym kawalkiem i poza nasza sesja.  Odpiecie
# gadzetu zrywa to samo polaczenie, ktorym wydajemy polecenia, wiec
# drugie wywolanie ssh nie ma juz dokad trafic.  Zmierzone 22.09.2026:
# w dwoch osobnych wywolaniach ginelo wlasnie to z resetem i telefon
# zostawal wlaczony, ale bez USB, do recznego wylaczenia.  Zadanie
# oddane systemd trwa dalej, kiedy nas juz nie ma.
$SSH "$UZYTKOWNIK@$ADRES" "cat > /tmp/restart-po-wgraniu.sh" <<'SKRYPT'
#!/bin/sh
sleep 2
sysctl -w kernel.sysrq=1 >/dev/null
sync; sync
for u in /sys/kernel/config/usb_gadget/*/UDC; do
	[ -e "$u" ] && echo > "$u"
done
echo s > /proc/sysrq-trigger
echo b > /proc/sysrq-trigger
SKRYPT
$SSH "$UZYTKOWNIK@$ADRES" "sudo systemd-run --unit=restart-po-wgraniu \
	--on-active=3 /bin/sh /tmp/restart-po-wgraniu.sh" || true
echo "telefon restartuje; wroci pod $ADRES za okolo minute"
