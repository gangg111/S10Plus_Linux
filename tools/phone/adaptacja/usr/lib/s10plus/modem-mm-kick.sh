#!/bin/sh
# Po starcie systemu ofono2mm (backend ModemManagera) potrafi odczytac stan karty
# SIM, zanim ofono zglosi Present=true, i zatrzasnac modem w stanie "failed /
# sim-missing", ktorego juz nie przelicza. Wskaznik sieci w Plasmie jest wtedy
# pusty mimo dzialajacej karty. Ta jednorazowka czeka, az ofono zobaczy karte,
# i jesli ModemManager stoi zepsuty, restartuje go raz (po restarcie czyta juz
# komplet wlasciwosci). Nie rusza nic, gdy modem jest zdrowy.
set -u

# 1) poczekaj, az ofono zobaczy karte (do ~60 s)
i=0
while [ "$i" -lt 30 ]; do
	if busctl --system call org.ofono /ril_0 org.ofono.SimManager GetProperties 2>/dev/null \
		| grep -q '"Present" b true'; then
		break
	fi
	i=$((i + 1))
	sleep 2
done

# brak karty: nie ma czego naprawiac
busctl --system call org.ofono /ril_0 org.ofono.SimManager GetProperties 2>/dev/null \
	| grep -q '"Present" b true' || exit 0

# 2) daj ModemManagerowi chwile na wlasna ocene
sleep 3

# 3) restartuj TYLKO jesli modem stoi failed albo nie widzi karty
modem=$(mmcli -L 2>/dev/null | grep -oE '/org/freedesktop/ModemManager1/Modem/[0-9]+' | head -n1)
state=""
[ -n "$modem" ] && state=$(mmcli -m "$modem" 2>/dev/null | sed -n 's/.*state: *//p' | head -n1 | tr -d ' ')

case "$state" in
	""|failed)
		systemctl restart ModemManager
		;;
esac

exit 0
