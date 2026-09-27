#!/bin/sh
# Wklada do obrazu pmOS WSZYSTKO, co ma przezyc wgranie, i sprawdza wynik.
#
# Po co ten skrypt istnieje. Wgranie partycji uzytkownika podmienia CALY system
# plikow, wiec kazda rzecz zainstalowana "na zywo" przez ssh znika bez sladu.
# Zdarzylo sie to juz dwa razy: raz z filtrem tok, raz z klawiatura ekranowa,
# ktora byla jedynym sposobem obslugi telefonu bez komputera. Za kazdym razem
# objaw wygladal jak awaria ("klawiatura nie dziala"), a przyczyna byla taka,
# ze danej rzeczy po prostu w obrazie nigdy nie bylo.
#
# Zasada: jesli cos ma byc na telefonie po wgraniu, MUSI byc w tym skrypcie.
# Na koncu jest audyt, ktory przerywa przy pierwszej niezgodnosci, zeby nie
# dalo sie wgrac obrazu z brakiem albo ze zlym wlascicielem.
#
# Uruchamiac jako root w WSL:
#   wsl.exe -d Debian -u root -- sh tools/phone/wszyj-wszystko-w-obraz.sh
set -e

D=/mnt/d/S10Plus-pmos
SUROWY=$D/pmos-nasza-seria.img
ROOT=/mnt/pmos-root
OFS_ROOT=511705088
LEN_ROOT=771751936
# Partycja rozruchowa obrazu: to na niej leza jadro, drzewo i initramfs.
BOOT=/mnt/pmos-boot
OFS_BOOT=8388608
LEN_BOOT=503316480
SPARSE=$D/pmos-nasza-seria.sparse.img

# Katalog z gotowymi artefaktami: tok-aarch64, tok-ssh, klucze, klawiatura,
# ter32x64.psf oraz pliki uslug.
PRZYBORY=${PRZYBORY:?ustaw PRZYBORY na katalog z artefaktami}

umount "$ROOT" 2>/dev/null || true
losetup -D 2>/dev/null || true
mkdir -p "$ROOT"
P=$(losetup --find --show --offset $OFS_ROOT --sizelimit $LEN_ROOT "$SUROWY")
trap 'umount "$ROOT" 2>/dev/null || true; umount "$BOOT" 2>/dev/null || true;
	losetup -d "$P" 2>/dev/null || true' EXIT
mount "$P" "$ROOT"

DOM="$ROOT/home/user"
UID_USER=$(awk -F: '$1 == "user" { print $3 }' "$ROOT/etc/passwd")
GID_USER=$(awk -F: '$1 == "user" { print $4 }' "$ROOT/etc/passwd")
[ -n "$UID_USER" ] && [ -n "$GID_USER" ] || {
	echo "nie umiem odczytac numeru konta user z obrazu"; exit 1; }
echo "== konto user w obrazie: $UID_USER:$GID_USER =="

echo
echo "== filtr tok =="
install -d -m 0755 -o "$UID_USER" -g "$GID_USER" "$DOM/.local" "$DOM/.local/bin"
install -m 0755 -o "$UID_USER" -g "$GID_USER" \
	"$PRZYBORY/tok-aarch64" "$DOM/.local/bin/tok"
tr -d '\r' < "$PRZYBORY/tok-ssh" > "$DOM/.local/bin/tok-ssh"
chmod 0755 "$DOM/.local/bin/tok-ssh"
chown "$UID_USER:$GID_USER" "$DOM/.local/bin/tok-ssh"

install -d -m 0700 -o "$UID_USER" -g "$GID_USER" "$DOM/.ssh"
{
	echo "# Klucz roboczy: KAZDE polecenie przechodzi przez tok."
	echo "# Ominiecie na zadanie: przedrostek TOK_RAW=1."
	printf 'command="/home/user/.local/bin/tok-ssh",no-agent-forwarding,no-port-forwarding,no-X11-forwarding %s\n' \
		"$(cat "$PRZYBORY/s10.pub")"
	echo "# Klucz ratunkowy: BEZ filtra, do przesylania plikow i na awarie."
	cat "$PRZYBORY/s10-ratunek.pub"
} > "$DOM/.ssh/authorized_keys"
chmod 0600 "$DOM/.ssh/authorized_keys"
chown "$UID_USER:$GID_USER" "$DOM/.ssh/authorized_keys"

echo
echo "== klawiatura ekranowa =="
# To jest jedyny sposob obslugi telefonu bez komputera, wiec brak tej pozycji
# w obrazie jest powazniejszy niz brak czegokolwiek innego ponizej.
install -m 0755 "$PRZYBORY/klawiatura" "$ROOT/usr/local/bin/klawiatura"
install -d -m 0755 "$ROOT/usr/share/consolefonts"
install -m 0644 "$PRZYBORY/ter32x64.psf" \
	"$ROOT/usr/share/consolefonts/ter32x64.psf"
for u in klawiatura.service czcionka-konsoli.service; do
	tr -d '\r' < "$PRZYBORY/$u" > "$ROOT/etc/systemd/system/$u"
	chmod 0644 "$ROOT/etc/systemd/system/$u"
	# Z sesja graficzna w obrazie klawiatura jest tylko trybem awaryjnym
	# (plasma-mobile.service.d/50-awaryjnie.conf), bo zabiera dotyk
	# i przyciski na wylacznosc; wpieta obok Plasmy dalaby martwy ekran.
	if [ "$u" = klawiatura.service ] &&
	   [ -L "$ROOT/etc/systemd/system/display-manager.service" ]; then
		echo "  sesja graficzna w obrazie: klawiatura tylko awaryjnie"
		continue
	fi
	ln -sf "../$u" \
		"$ROOT/etc/systemd/system/multi-user.target.wants/$u"
done
install -d -m 0755 "$ROOT/etc/systemd/system/plasma-mobile.service.d"
tr -d '\r' < "$PRZYBORY/plasma-mobile-awaryjnie.conf" \
	> "$ROOT/etc/systemd/system/plasma-mobile.service.d/50-awaryjnie.conf"
chmod 0644 "$ROOT/etc/systemd/system/plasma-mobile.service.d/50-awaryjnie.conf"

echo
echo "== klawiatura takze w initramfs =="
# Po co drugi raz.  Powyzsza kopia lezy w SYSTEMIE PLIKOW obrazu, wiec ginie
# przy kazdej wymianie korzenia: wgraniu cudzego obrazu, przywroceniu,
# wyczyszczeniu.  Kopia w initramfs jest odporna na to wszystko, bo initramfs
# dokłada brakujace pliki na KAZDY korzen tuz przed przejsciem na niego.
umount "$BOOT" 2>/dev/null || true
mkdir -p "$BOOT"
PB=$(losetup --find --show --offset $OFS_BOOT --sizelimit $LEN_BOOT "$SUROWY")
mount "$PB" "$BOOT"
sh "$(dirname "$0")/wszyj-klawiature-w-initramfs.sh" \
	"$BOOT/initramfs" "$BOOT/initramfs.nowy"
mv "$BOOT/initramfs.nowy" "$BOOT/initramfs"

echo
echo "== firmware Wi-Fi w initramfs =="
# Sterownik PCIe i brcmfmac sa wbudowane, wiec brcmfmac prosi o firmware
# przy starcie jadra, zanim zamontuje sie korzen z /lib/firmware; bez tych
# plikow w initramfs wlan0 nie powstaje (zmierzone 23.09.2026).  Pliki
# naleza do producenta i nie leza w repo: FIRMWARE_WIFI wskazuje katalog
# z brcmfmac4375-pcie.{bin,txt,clm_blob} wyjetymi z telefonu (NVRAM od B1).
# FIRMWARE_WIFI=pomin buduje obraz swiadomie bez Wi-Fi przy starcie.
if [ "${FIRMWARE_WIFI:-}" = pomin ]; then
	echo "  pominiete na zyczenie: obraz wstanie bez Wi-Fi"
elif [ -n "${FIRMWARE_WIFI:-}" ]; then
	FIRMWARE="$FIRMWARE_WIFI" sh "$(dirname "$0")/wszyj-firmware-wifi-w-initramfs.sh" \
		"$BOOT/initramfs" "$BOOT/initramfs.nowy"
	mv "$BOOT/initramfs.nowy" "$BOOT/initramfs"
else
	echo "  BRAK FIRMWARE_WIFI: audyt na koncu przerwie"
fi

# Osiem rdzeni zamiast jednego: wiersz rozruchowy NIE moze niesc maxcpus.
#
# Zmierzone 22.09.2026.  Parametr `maxcpus=1` lezal tam, bo bez niego telefon
# resetowal sie przy kazdej probie obudzenia rdzenia.  Przyczyna byla gdzie
# indziej: obraz jadra ladowal powyzej 4 GB, a firmware nie potrafi tam
# wystartowac rdzenia i zamiast bledu kladzie caly uklad.  Latka 0030
# bootloadera sprowadza obraz pod te granice, wiec powod zniknal.
#
# Sam parametr trzeba teraz zdjac, bo szkodzi: z nim jadro ustala zdolnosci
# systemu na podstawie jednego malego rdzenia i kazdy pozniej dobudzany duzy
# odrzuca wprost ("CPU5: will not boot", konflikt zdolnosci).  Bez niego
# wszystkie osiem sa obecne przy ustalaniu i wchodza bez sprzeciwu.
WPISY=$BOOT/loader/entries
if [ -f "$WPISY/00-s10.conf" ]; then
	# Droga powrotna zostaje obok, gdyby ktorys rdzen kiedys sprawial klopot.
	if [ ! -f "$WPISY/99-s10-jeden-rdzen.conf" ]; then
		sed 's/^title .*/title postmarketOS, jeden rdzen (awaryjny)/;
		     s/^sort-key .*/sort-key 99-s10-jeden/' \
			"$WPISY/00-s10.conf" > "$WPISY/99-s10-jeden-rdzen.conf"
		grep -q " maxcpus=" "$WPISY/99-s10-jeden-rdzen.conf" ||
			sed -i 's/^\(options .*\)$/\1 maxcpus=1/' \
				"$WPISY/99-s10-jeden-rdzen.conf"
	fi
	sed -i 's/ maxcpus=[0-9]*//' "$WPISY/00-s10.conf"

	# Cichy rozruch dopiero TERAZ, zeby wpis awaryjny wyzej zostal
	# gadatliwy: gdy rozruch stanie, jest to jedyna droga, ktora
	# cokolwiek powie.  Zmierzone 22.09.2026 na tym telefonie:
	#   - earlycon=efifb pisalo wczesne wiersze jadra WPROST po
	#     obrazku rozruchowym, wiec znika razem z reszta gadania,
	#   - bez logo-pos i logo-count jadro rysuje swoj znak raz na
	#     KAZDY rdzen online, czyli osiem sztuk w rzedzie przy
	#     gornej krawedzi panelu; z nimi jeden, na srodku.
	grep -q " quiet" "$WPISY/00-s10.conf" ||
		sed -i 's/^\(options .*\)$/\1 quiet systemd.show_status=false vt.global_cursor_default=0/' \
			"$WPISY/00-s10.conf"
	# loglevel 2, a nie 3: plymouth (ekran startowy pmOS, 7-10 s rozruchu)
	# czyta /dev/kmsg i sam wypisuje na czerwono kazdy komunikat o poziomie
	# NIE WYZSZYM niz prog z /proc/sys/kernel/printk, czyli przy 3 takze
	# bledy, ktorych jadro przy tym progu nie pokazuje.  Zmierzone 23.09.2026:
	# niegrozny "brcmf_dongle_roam: WLC_SET_ROAM_TRIGGER error (-52)"
	# z 9,77 s stal nad logowaniem.
	sed -i -e "s/ earlycon=efifb//" -e "s/ loglevel=[0-9]*/ loglevel=2/" \
		"$WPISY/00-s10.conf"
	grep -q "logo-pos:center" "$WPISY/00-s10.conf" ||
		sed -i "s/fbcon=font:TER16x32/fbcon=font:TER16x32,logo-pos:center,logo-count:1/" \
			"$WPISY/00-s10.conf"
	# Ochrona matrycy.  Panel tego telefonu to AMOLED, na ktorym kazdy
	# piksel starzeje sie proporcjonalnie do czasu swiecenia, a konsola
	# potrafi stac godzinami na jednym napisie logowania.  consoleblank
	# wygasza ja po dwoch minutach ciszy, jako siatka pod klawiatura, ktora gasi sama po 30 s: sciezka DRM dla sysfb zeruje
	# wtedy bufor obrazu, czyli piksele gasna naprawde.  panic dorzuca
	# restart po awarii, zeby jasny zrzut bledu nie zostal na ekranie
	# do wyczerpania baterii; trzydziesci sekund wystarcza, zeby go
	# sfotografowac.
	grep -q "consoleblank" "$WPISY/00-s10.conf" ||
		sed -i 's/^\(options .*\)$/\1 consoleblank=120 panic=30/' \
			"$WPISY/00-s10.conf"
	echo "  wiersz rozruchowy: bez maxcpus, cichy, logo na srodku, wygaszanie"
else
	echo "  UWAGA brak $WPISY/00-s10.conf, wiersza rozruchowego nie ruszono"
fi

# Menu rozruchowe bez odliczania.  Zmierzone 22.09.2026: pieciosekundowe
# odliczanie plus rysowanie menu na panelu 1440 na 3040 kosztowalo 17,3 s
# fazy loadera, a po wylaczeniu zostalo z niej 0,3 s; caly rozruch spadl
# z 31,7 s do 14,6 s.  Menu nadal wywoluje klawisz, wiec nic nie ginie.
if [ -f "$BOOT/loader/loader.conf" ]; then
	if grep -q "^timeout " "$BOOT/loader/loader.conf"; then
		sed -i "s/^timeout .*/timeout 0/" "$BOOT/loader/loader.conf"
	else
		printf "timeout 0\n" >> "$BOOT/loader/loader.conf"
	fi
	echo "  menu rozruchowe bez odliczania"
else
	echo "  UWAGA brak loader.conf, menu nie ruszono"
fi
sync
umount "$BOOT"
losetup -d "$PB"

echo
echo "== firmware ukladu lacznosci =="
install -m 0755 "$PRZYBORY/firmware-lacznosci.sh" \
	"$ROOT/usr/local/bin/firmware-lacznosci.sh"
# Lista dla mkinitfs: kazda przebudowa initramfs przez pmOS (np. przy
# aktualizacji pakietow) ma zabrac firmware Wi-Fi ze soba, inaczej po
# restarcie wbudowany brcmfmac go nie znajdzie (sprawdzone 23.09.2026:
# samo mkinitfs z ta lista wklada trzy pliki do initramfs).
install -d -m 0755 "$ROOT/etc/mkinitfs/files"
install -m 0644 "$(dirname "$0")/50-wifi-bcm4375.files" \
	"$ROOT/etc/mkinitfs/files/50-wifi-bcm4375.files"

echo
echo "== logo jadra ma dotrwac do logowania =="
# Getty domyslnie kasuje wirtualny terminal przy starcie
# (TTYVTDisallocate=yes) i logo jadra znika po niecalych pieciu
# sekundach, zostawiajac czarny ekran az do napisu logowania.  Na
# telefonie to jedyne, co w tym czasie widac, wiec ma zostac.
install -d -m 0755 "$ROOT/etc/systemd/system/getty@tty1.service.d"
printf '%s\n' \
	"# Bez tego getty kasuje ekran i logo jadra znika po pieciu sekundach." \
	"[Service]" \
	"TTYVTDisallocate=no" \
	> "$ROOT/etc/systemd/system/getty@tty1.service.d/10-zostaw-logo.conf"
chmod 0644 "$ROOT/etc/systemd/system/getty@tty1.service.d/10-zostaw-logo.conf"

echo
echo "== konsola loguje sama =="
# Na telefonie bez klawiatury fizycznej wpisywanie loginu i hasla palcem
# przy kazdym starcie nic nie chroni, a kosztuje.  Cena jest jawna: kto
# trzyma telefon w reku, ten ma powloke, a razem z regula sudo bez hasla
# nizej takze roota.  Usunac przed jakimkolwiek innym uzyciem systemu.
printf '%s\n' \
	"# Konsola na tty1 loguje uzytkownika user sama." \
	"[Service]" \
	"ExecStart=" \
	'ExecStart=-/usr/sbin/agetty --autologin user --noreset --noclear - ${TERM}' \
	> "$ROOT/etc/systemd/system/getty@tty1.service.d/20-autologowanie.conf"
chmod 0644 "$ROOT/etc/systemd/system/getty@tty1.service.d/20-autologowanie.conf"

echo
echo "== przycisk zasilania gasi ekran, nie telefon =="
# Klawiatura ekranowa obsluguje KEY_POWER sama: krotkie przycisniecie gasi
# i budzi panel.  Bez tej reguly systemd-logind wylaczylby caly system
# pierwszym przycisnieciem, bo taka ma domyslna polityke.  Dlugie
# przytrzymanie zostawiamy jako awaryjne wylaczenie.
install -d -m 0755 "$ROOT/etc/systemd/logind.conf.d"
printf '%s\n' \
	"# Przycisk zasilania gasi i budzi EKRAN; obsluguje go klawiatura." \
	"[Login]" \
	"HandlePowerKey=ignore" \
	"HandlePowerKeyLongPress=ignore" \
	> "$ROOT/etc/systemd/logind.conf.d/10-ekran.conf"
chmod 0644 "$ROOT/etc/systemd/logind.conf.d/10-ekran.conf"

echo
echo "== praca zdalna bez pytania o haslo =="
install -d -m 0750 "$ROOT/etc/sudoers.d"
printf '%s\n' \
	"# Telefon jest maszyna deweloperska tego portu; praca idzie po kablu." \
	"# Usunac przed jakimkolwiek innym uzyciem tego systemu." \
	"user ALL=(ALL) NOPASSWD: ALL" > "$ROOT/etc/sudoers.d/10-praca-zdalna"
chmod 0440 "$ROOT/etc/sudoers.d/10-praca-zdalna"

echo
echo "== audyt: nic nie moze byc pominiete ani zle nadane =="
zle=0
spr() {	# $1 sciezka  $2 prawa  $3 wlasciciel
	if [ ! -e "$ROOT/$1" ]; then
		echo "  BRAK       $1"; zle=$((zle+1)); return
	fi
	p=$(stat -c %a "$ROOT/$1"); w=$(stat -c %u:%g "$ROOT/$1")
	if [ "$p" = "$2" ] && [ "$w" = "$3" ]; then
		echo "  ok  $p $w  $1"
	else
		echo "  ZLE $p $w (ma byc $2 $3)  $1"; zle=$((zle+1))
	fi
}
spr home/user/.ssh                      700 "$UID_USER:$GID_USER"
spr home/user/.ssh/authorized_keys      600 "$UID_USER:$GID_USER"
spr home/user/.local/bin/tok            755 "$UID_USER:$GID_USER"
spr home/user/.local/bin/tok-ssh        755 "$UID_USER:$GID_USER"
spr usr/local/bin/klawiatura            755 0:0
spr usr/share/consolefonts/ter32x64.psf 644 0:0
spr etc/systemd/system/klawiatura.service        644 0:0
spr etc/systemd/system/czcionka-konsoli.service  644 0:0
spr usr/local/bin/firmware-lacznosci.sh 755 0:0
spr etc/mkinitfs/files/50-wifi-bcm4375.files 644 0:0
spr etc/sudoers.d/10-praca-zdalna       440 0:0
spr etc/systemd/system/getty@tty1.service.d/10-zostaw-logo.conf 644 0:0
spr etc/systemd/logind.conf.d/10-ekran.conf 644 0:0
spr etc/systemd/system/getty@tty1.service.d/20-autologowanie.conf 644 0:0
for u in klawiatura.service czcionka-konsoli.service; do
	if [ -L "$ROOT/etc/systemd/system/multi-user.target.wants/$u" ]; then
		echo "  ok  wpiete  $u"
	elif [ "$u" = klawiatura.service ] &&
	     [ -L "$ROOT/etc/systemd/system/display-manager.service" ] &&
	     [ -f "$ROOT/etc/systemd/system/plasma-mobile.service.d/50-awaryjnie.conf" ]; then
		echo "  ok  awaryjnie $u (sesja graficzna w obrazie)"
	else
		echo "  BRAK wpiecia $u"; zle=$((zle+1))
	fi
done

umount "$ROOT"
losetup -d "$P"
trap - EXIT
echo
# Hook w initramfs sprawdzamy osobno, bo lezy na innej partycji obrazu.
PB=$(losetup --find --show --offset $OFS_BOOT --sizelimit $LEN_BOOT "$SUROWY")
mkdir -p "$BOOT"
mount -o ro "$PB" "$BOOT"
if zstd -d -q -c "$BOOT/initramfs" |
   cpio -t --quiet 2>/dev/null | grep -q '^hooks-cleanup/50-klawiatura.sh$'; then
	echo "  ok  hook klawiatury w initramfs"
else
	echo "  BRAK hooka klawiatury w initramfs"; zle=$((zle+1))
fi
if [ "${FIRMWARE_WIFI:-}" = pomin ]; then
	echo "  UWAGA firmware Wi-Fi swiadomie pominiete"
elif zstd -d -q -c "$BOOT/initramfs" |
   cpio -t --quiet 2>/dev/null | grep -q '^lib/firmware/brcm/brcmfmac4375-pcie.bin$'; then
	echo "  ok  firmware Wi-Fi w initramfs"
else
	echo "  BRAK firmware Wi-Fi w initramfs (ustaw FIRMWARE_WIFI)"; zle=$((zle+1))
fi
if grep -q ' maxcpus=' "$BOOT/loader/entries/00-s10.conf" 2>/dev/null; then
	echo "  ZLE wiersz rozruchowy nadal ogranicza rdzenie"; zle=$((zle+1))
else
	echo "  ok  wiersz rozruchowy bez ograniczenia rdzeni"
fi
if [ -f "$BOOT/loader/entries/99-s10-jeden-rdzen.conf" ]; then
	echo "  ok  wpis awaryjny z jednym rdzeniem"
else
	echo "  BRAK wpisu awaryjnego z jednym rdzeniem"; zle=$((zle+1))
fi
W=$BOOT/loader/entries/00-s10.conf
if grep -q " quiet" "$W" && ! grep -q "earlycon" "$W"; then
	echo "  ok  wiersz rozruchowy cichy"
else
	echo "  ZLE wiersz rozruchowy nadal gada"; zle=$((zle+1))
fi
if grep -q "logo-pos:center" "$W" && grep -q "logo-count:1" "$W"; then
	echo "  ok  logo jadra jedno i na srodku"
else
	echo "  ZLE logo jadra nieustawione"; zle=$((zle+1))
fi
if grep -q "consoleblank=" "$W" && grep -q "panic=" "$W"; then
	echo "  ok  wygaszanie konsoli i restart po awarii"
else
	echo "  ZLE brak ochrony matrycy w wierszu rozruchowym"; zle=$((zle+1))
fi
if grep -q "^timeout 0" "$BOOT/loader/loader.conf" 2>/dev/null; then
	echo "  ok  menu rozruchowe bez odliczania"
else
	echo "  ZLE menu rozruchowe nadal odlicza"; zle=$((zle+1))
fi
# Droga awaryjna ma zostac gadatliwa, inaczej nie ma z czego czytac awarii.
if grep -q "earlycon" "$BOOT/loader/entries/99-s10-jeden-rdzen.conf" 2>/dev/null; then
	echo "  ok  wpis awaryjny nadal gadatliwy"
else
	echo "  ZLE wpis awaryjny tez wyciszony"; zle=$((zle+1))
fi
umount "$BOOT"; losetup -d "$PB"

[ "$zle" = 0 ] || { echo "audyt: $zle pozycji do poprawy, obraz NIE jest gotowy"; exit 1; }

echo
echo "== plik do wgrywania =="
# Fastboot wgrywa obraz RZADKI, a nie surowy.  Bez tego kroku wszystko powyzej
# lezy w pliku, ktorego nikt nie wysyla: zmierzone 22.09.2026, obraz rzadki byl
# o osiem godzin starszy od surowego, wiec caly wczorajszy wsad nie mial jak
# trafic na telefon.
command -v img2simg >/dev/null || {
	echo "brak img2simg (pakiet android-sdk-libsparse-utils)"; exit 1; }
img2simg "$SUROWY" "$SPARSE"
ls -l "$SUROWY" "$SPARSE" | awk '{printf "  %-46s %s B\n", $NF, $5}'
[ "$SPARSE" -nt "$SUROWY" ] || {
	echo "obraz rzadki NIE jest nowszy od surowego"; exit 1; }
echo "  ok  obraz rzadki nowszy od surowego"

# Odin jest droga zapasowa i jego pliku tu NIE odswiezamy: wazy tyle samo co
# obraz, a normalna praca idzie fastbootem.  Gdy jest starszy, mowimy o tym
# wprost, zeby nikt nie cofnal telefonu do tamtego stanu nie wiedzac o tym.
TAR=$D/pmos-userdata-sparse.tar.md5
if [ -f "$TAR" ] && [ "$TAR" -ot "$SUROWY" ]; then
	echo "  UWAGA plik dla Odina jest STARSZY od obrazu:"
	echo "        $TAR z $(date -r "$TAR" '+%Y-%m-%d %H:%M')"
	echo "        wgranie nim cofnie telefon do tamtego stanu"
fi

echo "audyt czysty, obraz gotowy: $SUROWY"
echo "do wgrania:   fastboot flash userdata $SPARSE"
