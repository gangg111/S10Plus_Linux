#!/bin/sh
# Wlacza radio modemu po starcie (ofono -> RIL -> modem). Bez Online=true modem
# Samsunga stoi w RADIO_OFF i karta SIM nie jest w ogole czytana. ofono potrzebuje
# chwili na wystawienie /ril_0, dlatego proby co 2 s przez 60 s.
set -u

i=1
while [ "$i" -le 30 ]; do
	if dbus-send --system --print-reply --dest=org.ofono /ril_0 \
		org.ofono.Modem.SetProperty string:"Online" variant:boolean:true >/dev/null 2>&1; then
		echo "radio wlaczone (proba $i)"
		exit 0
	fi
	i=$((i + 1))
	sleep 2
done

echo "nie udalo sie wlaczyc radia po 60 s"
exit 1
