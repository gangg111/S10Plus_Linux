#!/bin/sh
# cofnij.sh: przywraca stan sprzed zainstaluj.sh (preset i ~/.config/plasma-mobile/plasmamobilerc).
# Uruchamiac NA TELEFONIE jako user:
#   sh cofnij.sh                  najnowsza kopia z ~/.local/state/nakladka-pasek
#   sh cofnij.sh <katalog kopii>  wskazana kopia
# ~/.config/plasmamobilerc nie jest ruszany (nakladka go nie zmienia).

KATALOG=$(cd "$(dirname "$0")" && pwd)
. "$KATALOG/wspolne.sh"

if [ "$(id -u)" = "0" ]; then
    blad "uruchom jako user, nie root"; exit 2
fi

KOPIA="$1"
if [ -z "$KOPIA" ]; then
    KOPIA=$(ls -1d "$KOPIE"/kopia-* 2>/dev/null | tail -n1)
fi
if [ -z "$KOPIA" ] || [ ! -r "$KOPIA/manifest" ]; then
    blad "brak kopii (szukano w $KOPIE)"; exit 3
fi
log "Przywracam z: $KOPIA"
if [ -r "$KOPIA/wielkosc.txt" ]; then
    _w=$(cat "$KOPIA/wielkosc.txt")
    if [ -n "$_w" ]; then
        kwriteconfig6 --file plasmamobilerc --group General --key statusBarScaleFactor "$_w"
    else
        kwriteconfig6 --file plasmamobilerc --group General --key statusBarScaleFactor --delete
    fi
    systemctl --user restart plasma-plasmashell.service 2>/dev/null && sleep 8
fi

srodowisko_sesji

BLEDY=0
while IFS='|' read -r _n _p; do
    [ -n "$_p" ] || continue
    if [ "$_n" = "BRAK" ]; then
        [ -e "$_p" ] || continue
        case "$_p" in
            "$PRESET_KAT"/*)
                # usuwamy tylko preset z naszym znacznikiem
                if grep -qF "$ZNACZNIK" "$_p"; then
                    rm -f "$_p" && log "Usunieto $_p"
                else
                    log "Pomijam $_p: nie ma znacznika nakladki."
                fi ;;
            *)
                rm -f "$_p" && log "Usunieto $_p (envmanager odtworzy go przy logowaniu)" ;;
        esac
    else
        if cp -p "$KOPIA/pliki/$_n" "$_p"; then
            log "Przywrocono $_p"
        else
            blad "nie przywrocilem $_p"; BLEDY=1
        fi
    fi
done < "$KOPIA/manifest"

OBJ=$(sciezka_dbus)
if [ -z "$OBJ" ]; then
    log "Brak sesji na D-Bus: stan wroci przy nastepnym logowaniu."
    exit "$BLEDY"
fi

PRZED_L=$(sed -n 's/^przed_statusBarLeftPadding=//p' "$KOPIA/stan.txt")
PRZED_R=$(sed -n 's/^przed_statusBarRightPadding=//p' "$KOPIA/stan.txt")

sprawdz_dbus() {
    OBJ=$(sciezka_dbus)
    [ -n "$OBJ" ] || return 1
    DB_L=$(odczyt_dbus "$OBJ" statusBarLeftPadding)
    DB_R=$(odczyt_dbus "$OBJ" statusBarRightPadding)
    log "D-Bus $OBJ: statusBarLeftPadding=$DB_L (przed instalacja $PRZED_L), statusBarRightPadding=$DB_R (przed $PRZED_R)"
    if [ -z "$PRZED_L" ] || [ -z "$PRZED_R" ]; then
        log "Kopia nie ma wartosci sprzed instalacji; porownaj recznie."
        return 0
    fi
    zgodne "$DB_L" "$PRZED_L" && zgodne "$DB_R" "$PRZED_R"
}

przeladuj_na_zywo
sleep 1
if sprawdz_dbus; then
    log "Cofnieto."
    exit "$BLEDY"
fi
log "Na zywo nie weszlo, probuje restartu samej powloki."
restart_powloki
_r=$?
if [ "$_r" -eq 0 ] && sprawdz_dbus; then
    log "Cofnieto."
    exit "$BLEDY"
fi
[ "$_r" -eq 2 ] && exit "$BLEDY"
blad "Powloka nadal pokazuje inne wartosci; stan wroci po ponownym zalogowaniu."
exit 6
