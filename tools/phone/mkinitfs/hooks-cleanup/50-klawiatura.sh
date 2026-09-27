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
