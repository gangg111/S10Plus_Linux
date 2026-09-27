#!/bin/sh
# sprawdz.sh: pokazuje, co powloka NAPRAWDE dostala, i opcjonalnie robi zrzut ekranu.
# Uruchamiac NA TELEFONIE jako user (ekran wlaczony, gdy chcesz zrzut):
#   sh sprawdz.sh                 tylko stan
#   sh sprawdz.sh ~/pasek.png     stan + zrzut przez spectacle
# Zrzut na PC: ssh -i s10 user@172.16.42.1 'cat ~/pasek.png' > pasek.png

KATALOG=$(cd "$(dirname "$0")" && pwd)
. "$KATALOG/wspolne.sh"

srodowisko_sesji
id_urzadzenia && log "Urzadzenie: $ID_URZ ($ZRODLO_ID)" || log "Urzadzenie: nieznane"
PRESET="$PRESET_KAT/$ID_URZ.conf"
if [ -r "$PRESET" ]; then
    log "--- preset $PRESET"
    grep -v '^#' "$PRESET" | grep -v '^$'
else
    log "--- brak presetu uzytkownika $PRESET"
fi
log "--- $PLIK_ENV [Panels][WhenOnTop] (wpisuje envmanager przy logowaniu)"
[ -r "$PLIK_ENV" ] && awk '/^\[/{g=$0; next} g=="[Panels][WhenOnTop]" && NF{print}' "$PLIK_ENV"
if [ -r "$PLIK_USER" ]; then
    _u=$(awk '/^\[/{g=$0; next} g=="[Panels][WhenOnTop]" && NF{print}' "$PLIK_USER")
    [ -n "$_u" ] && { log "--- UWAGA: nadpisanie w $PLIK_USER [Panels][WhenOnTop]"; printf '%s\n' "$_u"; }
fi

if odczytaj_skale; then log "Skala: $SKALA ($ZRODLO_SKALI)"; else log "Skala: nieznana (podaj SKALA=...)"; fi

OBJ=$(sciezka_dbus)
if [ -z "$OBJ" ]; then
    log "plasmashell nie wystawia /Mobile/Panels na D-Bus."
    exit 1
fi
DB_L=$(odczyt_dbus "$OBJ" statusBarLeftPadding)
DB_R=$(odczyt_dbus "$OBJ" statusBarRightPadding)
DB_H=$(odczyt_dbus "$OBJ" statusBarHeight)
log "D-Bus $OBJ (px logiczne): statusBarLeftPadding=$DB_L statusBarRightPadding=$DB_R statusBarHeight=$DB_H"
if [ -n "$SKALA" ] && [ -n "$DB_L" ] && [ -n "$DB_R" ]; then
    awk -v s="$SKALA" -v a="$DB_L" -v b="$DB_R" -v k="$STALA_LP" -v w="$SZEROKOSC_PANELU" 'BEGIN{
        rp=(k+a)*s; lp=(k+b)*s;
        printf "Margines paska: prawy %.0f px (StatusBar.qml:79), lewy %.0f px (StatusBar.qml:80).\n", rp, lp;
        printf "Zawartosc paska: x od %.0f do %.0f. Wyciecie aparatu wg LineageOS: x 1114..1440, y 0..142.\n", lp, w-rp }'
fi

[ -n "$1" ] && zrzut "$1"
exit 0
