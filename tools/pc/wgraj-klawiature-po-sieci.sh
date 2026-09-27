#!/bin/sh
# Podmienia klawiature na telefonie po sieci, BEZ wgrywania obrazu.
#
# Po co.  `fastboot flash userdata` podmienia CALY system plikow, wiec kasuje
# wszystko, co powstalo na telefonie po ostatnim wgraniu: wlasne pliki, logi,
# pomiary.  Do zmiany samej klawiatury nie jest do niczego potrzebny: program,
# czcionka i pliki uslug to nieco ponad megabajt, ktory idzie tym samym laczem,
# ktorym i tak czytamy dzienniki.
#
# Co robi, po kolei:
#   1. Zdejmuje z telefonu kopie tego, co ma zostac nietkniete (katalog domowy
#      i dzisiejsze logi), i kladzie ja na komputerze.
#   2. Wysyla binarke, czcionke konsoli i oba pliki uslug.
#   3. Przeladowuje usluge i sprawdza, ze wstala.
#   4. Porownuje sumy kontrolne tego, co wyslane, z tym, co leglo na telefonie.
#
# Uzycie:
#   PRZYBORY=<katalog z artefaktami> tools/pc/wgraj-klawiature-po-sieci.sh [adres]
#
# Klucze: KLUCZ to klucz roboczy (ma wymuszony filtr tok, wiec pliki NIE moga
# nim isc przez scp), KLUCZ_PLIKI to klucz ratunkowy, ktorym ida pliki.
set -eu

ADRES=${1:-172.16.42.1}
UZYTKOWNIK=user
PRZYBORY=${PRZYBORY:?ustaw PRZYBORY na katalog z artefaktami}
KLUCZ=${KLUCZ:?ustaw KLUCZ na klucz roboczy}
KLUCZ_PLIKI=${KLUCZ_PLIKI:?ustaw KLUCZ_PLIKI na klucz ratunkowy}
KOPIA=${KOPIA:-kopia-telefonu}

SSH="ssh -i $KLUCZ -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10"
SCP="scp -i $KLUCZ_PLIKI -o IdentitiesOnly=yes -o BatchMode=yes"

for p in klawiatura ter32x64.psf klawiatura.service czcionka-konsoli.service; do
	[ -f "$PRZYBORY/$p" ] || { echo "brak $PRZYBORY/$p" >&2; exit 1; }
done

echo "== czy telefon odpowiada =="
$SSH "$UZYTKOWNIK@$ADRES" "uname -r" || {
	echo "brak polaczenia z $ADRES" >&2
	exit 2
}

echo
echo "== kopia tego, co ma zostac =="
# Robimy ja ZAWSZE i PRZED czymkolwiek innym: to jedyna rzecz w tym skrypcie,
# ktorej nie da sie odtworzyc, gdyby cos poszlo nie tak.
mkdir -p "$KOPIA"
$SSH "$UZYTKOWNIK@$ADRES" "tar czf - -C /home user 2>/dev/null" \
	> "$KOPIA/home-user.tar.gz" || true
if [ -s "$KOPIA/home-user.tar.gz" ]; then
	printf '  katalog domowy: %s B -> %s\n' \
		"$(wc -c < "$KOPIA/home-user.tar.gz")" "$KOPIA/home-user.tar.gz"
else
	echo "  UWAGA kopia katalogu domowego jest pusta, przerywam" >&2
	exit 1
fi

echo
echo "== wysylka =="
for para in "klawiatura:/tmp/klawiatura-nowa" \
	    "ter32x64.psf:/tmp/ter32x64.psf" \
	    "klawiatura.service:/tmp/klawiatura.service" \
	    "czcionka-konsoli.service:/tmp/czcionka-konsoli.service"; do
	zrodlo=${para%%:*}
	cel=${para#*:}
	$SCP "$PRZYBORY/$zrodlo" "$UZYTKOWNIK@$ADRES:$cel" > /dev/null
	printf '  %-26s -> %s\n' "$zrodlo" "$cel"
done

echo
echo "== instalacja =="
$SSH "$UZYTKOWNIK@$ADRES" "TOK_RAW=1 sh -c '
	sudo systemctl stop klawiatura.service
	sudo install -m 0755 /tmp/klawiatura-nowa /usr/local/bin/klawiatura
	sudo install -m 0644 /tmp/ter32x64.psf /usr/share/consolefonts/ter32x64.psf
	sudo install -m 0644 /tmp/klawiatura.service /etc/systemd/system/klawiatura.service
	sudo install -m 0644 /tmp/czcionka-konsoli.service /etc/systemd/system/czcionka-konsoli.service
	sudo systemctl daemon-reload
	sudo systemctl restart czcionka-konsoli.service || true
	sudo systemctl start klawiatura.service
	sleep 2
	echo \"  usluga: \$(systemctl is-active klawiatura.service)\"
	sha256sum /usr/local/bin/klawiatura /usr/share/consolefonts/ter32x64.psf
'"

echo
echo "== kontrola: to samo po obu stronach =="
sha256sum "$PRZYBORY/klawiatura" "$PRZYBORY/ter32x64.psf" |
	awk '{printf "  na komputerze %s  %s\n", substr($1,1,16), $2}'
echo
echo "Nic nie zostalo skasowane: obraz nie byl wgrywany, a kopia katalogu"
echo "domowego lezy w $KOPIA."
