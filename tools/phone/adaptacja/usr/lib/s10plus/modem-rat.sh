#!/bin/sh
# Wypisuje krotkie oznaczenie technologii sieci komorkowej (jak w One UI):
# 5G / LTE / H+ / 3G / E / 2G, albo nic, gdy modem nie jest zarejestrowany.
# Czytane z ModemManagera (ten sam, ktory zasila wskaznik Plasmy), wiec dziala
# dla uzytkownika sesji. Wywolywane cyklicznie przez DataSource panelu.
set -eu

modem=$(mmcli -L 2>/dev/null | grep -oE '/org/freedesktop/ModemManager1/Modem/[0-9]+' | head -n1)
[ -n "$modem" ] || exit 0

info=$(mmcli -m "$modem" 2>/dev/null) || exit 0

state=$(printf '%s\n' "$info" | sed -n 's/.*state: *//p' | head -n1 | tr -d ' ')
case "$state" in
	registered|connected|roaming) ;;
	*) exit 0 ;;  # szukanie/wylaczony/failed: bez napisu
esac

tech=$(printf '%s\n' "$info" | sed -n 's/.*access tech: *//p' | head -n1)

# access tech moze byc lista po przecinku (np. "lte, 5gnr"); bierzemy najwyzsza
case "$tech" in
	*5gnr*|*5g*|*nr*) echo "5G" ;;
	*lte*)            echo "LTE" ;;
	*hspa*|*hsdpa*|*hsupa*|*dc-hspa*) echo "H+" ;;
	*umts*)           echo "3G" ;;
	*edge*)           echo "E" ;;
	*gprs*|*gsm*)     echo "2G" ;;
	*)                : ;;  # nieznana: bez napisu
esac
