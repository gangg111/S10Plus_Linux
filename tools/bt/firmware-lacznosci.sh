#!/bin/sh
# Wyjmuje z partycji producenta firmware obu polowek ukladu lacznosci.
#
# Po co.  Uklad BCM4375 po wlaczeniu zasilania umie tylko tyle, zeby odpowiedziec
# na pierwsze polecenia; cala reszta, razem z wlasnym adresem, przychodzi z plikow
# lat, ktore host wgrywa przy kazdym starcie.  Pliki naleza do telefonu i leza na
# jego partycji producenta, wiec bierzemy je stamtad, zamiast szukac w sieci.
#
# Dwie polowki, dwa rodzaje plikow:
#   Bluetooth: plik .hcd, ktorego sterownik hci_bcm szuka pod nazwa zbudowana
#     z nazwy ukladu.  Tablica tego sterownika nie zna BCM4375, wiec nazwa
#     wychodzi zapasowa, brcm/BCM.hcd, i pod taka go kladziemy.
#   Wi-Fi: obraz ukladu i jego kalibracja.  Producent trzyma je pod nazwami
#     bcmdhd*.bin i nvram*.txt, bo uzywa swojego sterownika; mainline'owy
#     brcmfmac szuka brcmfmac4375-pcie.bin i .txt.  Kopiujemy pod obiema
#     nazwami: oryginalna dla sladu, docelowa dla sterownika.
#
# UWAGA, to jest hipoteza do sprawdzenia: obrazy dla obu sterownikow wywodza sie
# z tego samego kodu Broadcoma i na PCIe uzywaja tego samego protokolu, ale nie
# ma dowodu, ze sa wymienne.  Jesli brcmfmac odrzuci obraz, bedzie to widac
# w logu jako blad przy wgrywaniu lat.
set -u

RAPORT=/var/log/firmware-lacznosci.txt
DOCELOWY=/lib/firmware/brcm
MNT=/mnt/vendor-ro
WGRANE=0

log() {
	echo "$*"
	echo "$*" >> "$RAPORT"
}

: > "$RAPORT"
log "== firmware ukladu lacznosci, $(date) =="

mkdir -p "$DOCELOWY"

# Uklad w tym telefonie to rewizja B1 (Bluetooth zglasza BCM4375B1), a obraz
# Wi-Fi producenta istnieje tylko jako _b1, wiec NVRAM tez musi byc od B1.
# Na partycji leza dwa: Semco (nvram.txt_CS01_semco_b1, modul "SWB-E43")
# i Murata (nvram.txt_1rh_es43_b1, modul "1RH").  Ktory modul jest wlutowany,
# mowi dopiero OTP ukladu, a tego brcmfmac dla 4375 nie czyta; wybrany jest
# Semco, z ktorym skan widzi sieci na 2,4 i 5 GHz (23.09.2026).  Gdyby radio
# szlo slabo, pierwszy do sprawdzenia jest wariant Murata.
MODUL=${MODUL:-semco}

# Dawniej brany byl pierwszy znaleziony NVRAM, czyli wariant b0 od innej
# rewizji; plik, ktory juz lezy, liczy sie wiec jako gotowy tylko wtedy, gdy
# jest od B1.
nvram_b1() {
	head -1 "$DOCELOWY/brcmfmac4375-pcie.txt" 2>/dev/null | grep -q 'B1'
}

if [ -f "$DOCELOWY/BCM.hcd" ] && [ -f "$DOCELOWY/brcmfmac4375-pcie.bin" ] &&
   nvram_b1; then
	log "pliki juz sa na miejscu (NVRAM od B1), nie ruszam partycji producenta"
else
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
			log "== co lezy w katalogu firmware =="
			ls -l "$MNT/firmware" 2>/dev/null | head -40 >> "$RAPORT"

			# Bluetooth
			HCD=$(find "$MNT" -iname "bcm4375B1_${MODUL}.hcd" 2>/dev/null | head -1)
			[ -z "$HCD" ] && HCD=$(find "$MNT" -iname '*B1*.hcd' \
					       2>/dev/null | head -1)
			[ -z "$HCD" ] && HCD=$(find "$MNT" -iname '*.hcd' 					       2>/dev/null | head -1)
			if [ -n "$HCD" ]; then
				cp "$HCD" "$DOCELOWY/$(basename "$HCD")"
				cp "$HCD" "$DOCELOWY/BCM.hcd"
				WGRANE=1
				log "Bluetooth: $(basename "$HCD") -> BCM.hcd,"\
				    "$(stat -c %s "$HCD") B"
			else
				log "BLAD: nie ma pliku .hcd na partycji"
			fi

			# Wi-Fi: obraz ukladu
			BIN=$(find "$MNT" -iname 'bcmdhd*sta*.bin*' 2>/dev/null | head -1)
			[ -z "$BIN" ] && BIN=$(find "$MNT" -iname 'bcmdhd*.bin*' \
					       2>/dev/null | head -1)
			if [ -n "$BIN" ]; then
				cp "$BIN" "$DOCELOWY/$(basename "$BIN")"
				cp "$BIN" "$DOCELOWY/brcmfmac4375-pcie.bin"
				log "Wi-Fi obraz: $(basename "$BIN") ->"\
				    "brcmfmac4375-pcie.bin, $(stat -c %s "$BIN") B"
			else
				log "BLAD: nie ma obrazu Wi-Fi na partycji"
			fi

			# Wi-Fi: kalibracja
			case $MODUL in
			murata) WZOR='nvram.txt_1rh_*_b1' ;;
			*)      WZOR="nvram.txt_*_${MODUL}_b1" ;;
			esac
			NVRAM=$(find "$MNT" -iname "$WZOR" 2>/dev/null | head -1)
			[ -z "$NVRAM" ] && NVRAM=$(find "$MNT" -iname 'nvram*_b1' \
					       2>/dev/null | head -1)
			[ -z "$NVRAM" ] && log "BLAD: nie ma NVRAM od rewizji B1"
			if [ -n "$NVRAM" ]; then
				cp "$NVRAM" "$DOCELOWY/$(basename "$NVRAM")"
				cp "$NVRAM" "$DOCELOWY/brcmfmac4375-pcie.txt"
				log "Wi-Fi kalibracja: $(basename "$NVRAM") ->"\
				    "brcmfmac4375-pcie.txt"
			fi

			# Wi-Fi: blob kodow krajowych, jesli jest
			CLM=$(find "$MNT" -iname '*clm*.blob' 2>/dev/null | head -1)
			if [ -n "$CLM" ]; then
				cp "$CLM" "$DOCELOWY/brcmfmac4375-pcie.clm_blob"
				log "Wi-Fi kody krajowe: $(basename "$CLM")"
			fi

			umount "$MNT"
			log "sumy:"
			sha256sum "$DOCELOWY"/* 2>/dev/null | cut -c1-20,65- \
				>> "$RAPORT"
		else
			log "BLAD: nie moge zamontowac $VENDOR"
		fi
	fi
fi

# Sterownik Bluetootha szukal firmware przy starcie, kiedy tego katalogu jeszcze
# nie bylo, i poszedl dalej BEZ lat: uklad istnieje, ale nie ma ani adresu, ani
# pelnej obslugi.  Dlatego ponawiamy probe zawsze, gdy plik wlasnie doszedl.
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
dmesg | grep -iE "BCM.*Patch|firmware Patch file not found|brcm/|brcmf" \
	| tail -12 >> "$RAPORT"
log "== co widzi jadro =="
dmesg | grep -iE "bluetooth|hci_uart|bcm|serial1|10840000|peric1" | tail -30 \
	>> "$RAPORT"
log "== urzadzenia HCI =="
ls /sys/class/bluetooth/ 2>/dev/null >> "$RAPORT" || echo "brak" >> "$RAPORT"
log "== adres kontrolera =="
hciconfig -a 2>/dev/null | head -12 >> "$RAPORT" || echo "brak hciconfig" \
	>> "$RAPORT"
log "== port szeregowy =="
ls /sys/bus/serial/devices/ 2>/dev/null >> "$RAPORT" || echo "brak" >> "$RAPORT"
log "== zegary PERIC1 =="
grep -iE "peric1|uart_bt" /sys/kernel/debug/clk/clk_summary 2>/dev/null \
	>> "$RAPORT"

exit 0
