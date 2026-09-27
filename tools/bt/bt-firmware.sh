#!/bin/sh
# Wyjmuje firmware ukladu Bluetooth z partycji producenta i podaje je jadru.
#
# Po co.  Uklad BCM4375 po wlaczeniu zasilania umie tylko tyle, zeby odpowiedziec
# na pierwsze polecenia; cala reszta, razem z wlasnym adresem, przychodzi z pliku
# lat, ktory host wgrywa przy kazdym starcie.  Plik nalezy do telefonu i lezy na
# jego partycji producenta, wiec bierzemy go stamtad, zamiast szukac w sieci.
#
# Pod jaka nazwa.  Sterownik buduje nazwe pliku z nazwy ukladu, ktora odczytuje
# z samego ukladu i tlumaczy przez wlasna tablice.  Tablica nie zna BCM4375,
# wiec nazwa wychodzi ZAPASOWA: brcm/BCM.hcd.  Kopiujemy wiec plik wlasnie tam,
# a pod oryginalna nazwa tylko dla porzadku, zeby bylo widac, co przyszlo
# z telefonu.  Gdy uklad zostanie kiedys dopisany do tablicy sterownika, nazwa
# docelowa sie zmieni i ten skrypt trzeba bedzie poprawic; raport nizej wypisuje
# nazwy, ktorych jadro naprawde szukalo, wiec widac to bez zgadywania.
#
# Raport laduje na partycji z logami, zeby dalo sie go przeczytac bez powloki.
set -u

RAPORT=/var/log/bluetooth-firmware.txt
DOCELOWY=/lib/firmware/brcm
MNT=/mnt/vendor-ro
WGRANE=0

log() {
	echo "$*"
	echo "$*" >> "$RAPORT"
}

: > "$RAPORT"
log "== firmware Bluetootha, $(date) =="

mkdir -p "$DOCELOWY"

if [ -f "$DOCELOWY/BCM.hcd" ]; then
	log "plik juz jest na miejscu, nie ruszam partycji producenta"
else
	# Partycja producenta: najpierw po nazwie, a gdy jadro nie robi dowiazan
	# po nazwach, po numerze z mapy partycji tego telefonu (sda26).
	VENDOR=""
	for k in /dev/block/by-name/vendor /dev/disk/by-partlabel/vendor \
	         /dev/sda26 /dev/block/sda26; do
		[ -b "$k" ] && { VENDOR=$k; break; }
	done

	if [ -z "$VENDOR" ]; then
		log "BLAD: nie znalazlem partycji producenta"
		log "urzadzenia blokowe: $(ls /dev/sd* 2>/dev/null | tr '\n' ' ')"
	else
		log "partycja producenta: $VENDOR"
		mkdir -p "$MNT"
		if mount -o ro "$VENDOR" "$MNT" 2>>"$RAPORT"; then
			ZNALEZIONE=$(find "$MNT" -iname '*.hcd' 2>/dev/null)
			if [ -z "$ZNALEZIONE" ]; then
				log "BLAD: na partycji nie ma zadnego pliku .hcd"
				log "katalogi firmware: $(ls "$MNT"/firmware 2>/dev/null | tr '\n' ' ')"
			else
				for f in $ZNALEZIONE; do
					log "znalezione: $f  $(stat -c %s "$f") B"
					cp "$f" "$DOCELOWY/$(basename "$f")"
				done
				PIERWSZY=$(echo "$ZNALEZIONE" | head -1)
				cp "$PIERWSZY" "$DOCELOWY/BCM.hcd"
				WGRANE=1
				log "skopiowane jako $DOCELOWY/BCM.hcd"
				log "suma: $(sha256sum "$DOCELOWY/BCM.hcd" | cut -c1-32)"
			fi
			umount "$MNT"
		else
			log "BLAD: nie moge zamontowac $VENDOR"
		fi
	fi
fi

# Sterownik szukal firmware przy starcie, kiedy tego katalogu jeszcze nie bylo,
# i poszedl dalej BEZ lat: uklad istnieje, ale nie ma ani adresu, ani pelnej
# obslugi.  Dlatego ponawiamy probe zawsze, gdy plik wlasnie doszedl, a nie
# dopiero wtedy, gdy kontrolera nie ma w ogole.
if [ "$WGRANE" = 1 ]; then
	STEROWNIK=/sys/bus/serial/drivers/hci_uart_bcm
	if [ -d "$STEROWNIK" ]; then
		for u in "$STEROWNIK"/serial*; do
			[ -e "$u" ] || continue
			N=$(basename "$u")
			log "ponawiam probe urzadzenia $N"
			echo "$N" > "$STEROWNIK/unbind" 2>>"$RAPORT"
			sleep 1
			echo "$N" > "$STEROWNIK/bind" 2>>"$RAPORT"
			sleep 3
		done
	else
		log "sterownik hci_uart_bcm nie ma katalogu w sysfs"
	fi
fi

log ""
log "== czego jadro szukalo =="
dmesg | grep -iE "BCM.*Patch|firmware Patch file not found|brcm/" | tail -10 >> "$RAPORT"
log "== co widzi jadro =="
dmesg | grep -iE "bluetooth|hci_uart|bcm|serial1|10840000|peric1" | tail -40 >> "$RAPORT"
log "== urzadzenia HCI =="
ls /sys/class/bluetooth/ 2>/dev/null >> "$RAPORT" || echo "brak" >> "$RAPORT"
log "== adres kontrolera =="
hciconfig -a 2>/dev/null | head -12 >> "$RAPORT" || echo "brak hciconfig" >> "$RAPORT"
log "== port szeregowy =="
ls /sys/bus/serial/devices/ 2>/dev/null >> "$RAPORT" || echo "brak" >> "$RAPORT"
log "== zegary PERIC1 =="
grep -iE "peric1|uart_bt" /sys/kernel/debug/clk/clk_summary 2>/dev/null >> "$RAPORT"

# Kopia raportu tam, gdzie komputer widzi ja jako zwykly plik na dysku.
for k in /mnt/logi /media/logi /var/log; do
	[ -d "$k" ] && cp "$RAPORT" "$k/bluetooth-firmware.txt" 2>/dev/null
done
exit 0
