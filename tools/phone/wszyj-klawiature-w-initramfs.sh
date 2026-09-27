#!/bin/sh
# Wklada klawiature ekranowa do initramfs, zeby wracala na KAZDY system plikow.
#
# Po co to istnieje.  Program klawiatury, jego czcionka i pliki uslug leza
# w systemie plikow, a ten wymienia sie w CALOSCI przy wgraniu partycji
# uzytkownika.  Zdarzylo sie to juz dwa razy i za kazdym razem objaw wygladal
# jak awaria klawiatury ("nie dziala"), a przyczyna byla taka, ze jej tam po
# prostu nie bylo.  Wszycie w obraz (tools/phone/wszyj-wszystko-w-obraz.sh)
# zalatwia obrazy, ktore sami budujemy; ten skrypt zalatwia KAZDY inny
# przypadek: korzen wgrany skadinad, przywrocony, wyczyszczony albo zlozony
# z innej wersji.
#
# Jak to dziala.  Initramfs pmOS wola wszystkie skrypty z katalogu
# /hooks-cleanup tuz przed switch_root, gdy docelowy korzen jest juz
# zamontowany na ZAPIS (init_2nd.sh: mount_root_partition w wierszu 53,
# run_hooks /hooks-cleanup w wierszu 67, switch_root w wierszu 106).  Kladziemy
# tam jeden skrypt i obok niego ladunek, a skrypt dokłada brakujace pliki.
#
# Uzycie:
#   PRZYBORY=<katalog z artefaktami> tools/phone/wszyj-klawiature-w-initramfs.sh \
#       <initramfs wejsciowy> <initramfs wyjsciowy>
#
# Wymaga roota (cpio odtwarza wlascicieli i urzadzenia) oraz zstd i cpio.
set -eu

WE=${1:?podaj plik initramfs wejsciowy}
WY=${2:?podaj plik initramfs wyjsciowy}
PRZYBORY=${PRZYBORY:?ustaw PRZYBORY na katalog z artefaktami}

for n in zstd cpio; do
	command -v "$n" >/dev/null || { echo "brak narzedzia $n" >&2; exit 1; }
done
for p in klawiatura ter32x64.psf klawiatura.service czcionka-konsoli.service; do
	[ -f "$PRZYBORY/$p" ] || { echo "brak $PRZYBORY/$p" >&2; exit 1; }
done

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
install -d -m 0755 "$KORZEN/usr/share/klawiatura"
install -m 0755 "$PRZYBORY/klawiatura" "$KORZEN/usr/share/klawiatura/klawiatura"
install -m 0644 "$PRZYBORY/ter32x64.psf" "$KORZEN/usr/share/klawiatura/ter32x64.psf"
for u in klawiatura.service czcionka-konsoli.service; do
	tr -d '\r' < "$PRZYBORY/$u" > "$KORZEN/usr/share/klawiatura/$u"
	chmod 0644 "$KORZEN/usr/share/klawiatura/$u"
done

cat > "$KORZEN/hooks-cleanup/50-klawiatura.sh" <<'HOOK'
#!/bin/sh
# Klawiatura ekranowa wraca na kazdy korzen, na ktorym jej nie ma.
#
# Uruchamiane przez initramfs pmOS tuz przed switch_root, gdy /sysroot jest
# zamontowany na zapis.  Init nie ma "set -e", wiec blad tego skryptu nie
# zatrzyma rozruchu; mimo to kazda operacja jest osobno zabezpieczona.
#
# Zasada: dokladamy TYLKO to, czego brakuje.  Wersji wgranej recznie do prob
# nie nadpisujemy, bo to odbieraloby mozliwosc sprawdzenia nowej binarki bez
# przebudowy initramfs.
Z=/usr/share/klawiatura
S=/sysroot

log() { echo "klawiatura-hook: $*" > /dev/kmsg 2>/dev/null || true; }

[ -d "$Z" ] || exit 0
[ -d "$S/usr" ] || { log "brak /sysroot/usr, pomijam"; exit 0; }

dolozonych=0

wstaw() {	# $1 nazwa w ladunku, $2 sciezka na korzeniu, $3 prawa
	[ -e "$S$2" ] && return 0
	mkdir -p "$(dirname "$S$2")" 2>/dev/null || return 0
	cp "$Z/$1" "$S$2" 2>/dev/null || { log "nie udalo sie wstawic $2"; return 0; }
	chmod "$3" "$S$2" 2>/dev/null || true
	chown 0:0 "$S$2" 2>/dev/null || true
	dolozonych=$((dolozonych + 1))
	log "dolozone $2"
}

wstaw klawiatura /usr/local/bin/klawiatura 0755
wstaw ter32x64.psf /usr/share/consolefonts/ter32x64.psf 0644
wstaw klawiatura.service /etc/systemd/system/klawiatura.service 0644
wstaw czcionka-konsoli.service /etc/systemd/system/czcionka-konsoli.service 0644

# Systemd jeszcze nie dziala, wiec wpiecie robimy dowiazaniem, dokladnie tym
# samym, ktore zrobilby "systemctl enable".
for u in klawiatura.service czcionka-konsoli.service; do
	# Przy sesji graficznej klawiatura jest tylko trybem awaryjnym: wpieta
	# obok Plasmy zabralaby jej dotyk i przyciski (EVIOCGRAB).  Test przez -L,
	# bo alias moze wskazywac plik spoza /sysroot.
	if [ "$u" = klawiatura.service ] &&
	   [ -L "$S/etc/systemd/system/display-manager.service" ]; then
		log "sesja graficzna, klawiatury nie wpinam"
		continue
	fi
	cel="$S/etc/systemd/system/multi-user.target.wants/$u"
	[ -e "$cel" ] && continue
	[ -e "$S/etc/systemd/system/$u" ] || continue
	mkdir -p "$(dirname "$cel")" 2>/dev/null || continue
	ln -sf "../$u" "$cel" 2>/dev/null && log "wpiete $u"
done

[ "$dolozonych" -gt 0 ] && log "dolozono $dolozonych plikow"
exit 0
HOOK
chmod 0755 "$KORZEN/hooks-cleanup/50-klawiatura.sh"

# Staly czas na CALYM drzewie.
#
# Dlaczego na calym, a nie tylko na tym, co dolozylismy.  cpio z flaga
# --reproducible zeruje numery urzadzenia i i-wezla, ale czasu modyfikacji
# NIE, a przy rozpakowywaniu nie odtwarza czasu KATALOGOW, do ktorych wlasnie
# wypakowal pliki.  Zmierzone: dwa przebiegi roznily sie w naglowku pozycji
# "etc" o szesc sekund (0x6AB249C6 wobec 0x6AB249CC), czyli o czas samego
# rozpakowania.  Czas plikow w initramfs nie znaczy nic ani dla jadra, ani dla
# init pmOS, a daje nam wynik powtarzalny co do bajtu, wiec da sie go przypiac
# suma kontrolna.  Dowiazan nie sledzimy (-h), bo czesc z nich celowo wskazuje
# na pliki spoza initramfs.
find "$KORZEN" -exec touch -h -d @0 {} +

echo "== spakowanie =="
# Ten sam format, co pmOS (newc) i ta sama kompresja (zstd).  --reproducible
# zeruje znaczniki czasu, wiec dwa przebiegi z tym samym ladunkiem daja
# identyczny plik i da sie to sprawdzic suma kontrolna.
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
for p in hooks-cleanup/50-klawiatura.sh usr/share/klawiatura/klawiatura \
	 usr/share/klawiatura/ter32x64.psf \
	 usr/share/klawiatura/klawiatura.service \
	 usr/share/klawiatura/czcionka-konsoli.service \
	 init init_2nd.sh init_functions.sh bin/busybox; do
	if [ -e "$SPR/$p" ]; then
		echo "  ok   $p"
	else
		echo "  BRAK $p"; zle=$((zle + 1))
	fi
done
[ -x "$SPR/hooks-cleanup/50-klawiatura.sh" ] || {
	echo "  BRAK bitu wykonywania na hooku"; zle=$((zle + 1)); }

ls -l "$WE" "$WY" | awk '{printf "  %-52s %s B\n", $NF, $5}'
[ "$zle" = 0 ] || { echo "audyt: $zle brakow, NIE uzywaj tego pliku" >&2; exit 1; }
echo "audyt czysty"
