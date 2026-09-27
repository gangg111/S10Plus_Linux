#!/bin/sh
# zainstaluj.sh: odsuwa zawartosc paska stanu Plasma Mobile od otworu aparatu
# (prawy gorny rog) i od zakrzywionej lewej krawedzi. Galaxy S10+, postmarketOS.
#
# Uruchamiac NA TELEFONIE jako user (nie root), z katalogu nakladki:
#   sh zainstaluj.sh                       cele domyslne: prawy 350 px, lewy 120 px
#   sh zainstaluj.sh 350 140               wlasne cele (px natywne od krawedzi)
#   sh zainstaluj.sh 350 120 142           dodatkowo wysokosc paska 142 px (jak Android)
#   SKALA=3 sh zainstaluj.sh               wymus skale, gdy kscreen-doctor jej nie poda
#   sh zainstaluj.sh --pokaz 3 [cele...]   tylko wypisz preset dla skali 3, nic nie zmienia
#
# Co robi: kopia stanu -> preset uzytkownika -> zastosowanie na zywo (sygnal KConfig),
# a gdy nie zadziala: restart samego plasmashell; na koniec sprawdza wartosci na D-Bus.
# Nie dotyka /usr ani /etc. Cofniecie: sh cofnij.sh

KATALOG=$(cd "$(dirname "$0")" && pwd)
. "$KATALOG/wspolne.sh"

POKAZ=""
if [ "$1" = "--pokaz" ]; then
    POKAZ=1
    SKALA="$2"
    shift 2
fi
CEL_PRAWY="${1:-$CEL_PRAWY_DOMYSLNY}"
CEL_LEWY="${2:-$CEL_LEWY_DOMYSLNY}"
WYSOKOSC="${3:-$WYSOKOSC_DOMYSLNA}"
WIELKOSC="${WIELKOSC:-$WIELKOSC_DOMYSLNA}"

for _v in "$CEL_PRAWY" "$CEL_LEWY"; do
    liczba "$_v" || { blad "cel '$_v' nie jest liczba"; exit 2; }
done
if [ -n "$WYSOKOSC" ] && ! liczba "$WYSOKOSC"; then
    blad "wysokosc '$WYSOKOSC' nie jest liczba"; exit 2
fi

if [ -n "$POKAZ" ]; then
    liczba "$SKALA" || { blad "podaj skale: --pokaz 3"; exit 2; }
    oblicz "$CEL_PRAWY" "$CEL_LEWY" "$SKALA"
    tresc_presetu "$SKALA" "$CEL_PRAWY" "$CEL_LEWY" "$WYSOKOSC"
    exit 0
fi

if [ "$(id -u)" = "0" ]; then
    blad "uruchom jako user, nie root (preset ma trafic do /home/user)"; exit 2
fi

srodowisko_sesji
id_urzadzenia || { blad "nie umiem ustalic id urzadzenia"; exit 3; }
if ! odczytaj_skale; then
    blad "nie odczytalem skali (kscreen-doctor -o nie podal 'Scale:')."
    blad "Sprawdz: kscreen-doctor -o | grep -i scale  i uruchom: SKALA=<wartosc> sh zainstaluj.sh"
    exit 3
fi
oblicz "$CEL_PRAWY" "$CEL_LEWY" "$SKALA"
PRESET="$PRESET_KAT/$ID_URZ.conf"

log "Urzadzenie: $ID_URZ ($ZRODLO_ID)"
log "Skala: $SKALA ($ZRODLO_SKALI)"
log "Preset: $PRESET  leftPadding=$PLIK_PRAWY rightPadding=$PLIK_LEWY ${WYSOKOSC:+statusBarHeight=$WYSOKOSC}"

# Nadpisanie w ~/.config/plasmamobilerc wygrywa z presetem; wtedy nakladka nic nie da.
NADPIS=""
if [ -r "$PLIK_USER" ]; then
    NADPIS=$(awk '/^\[/{g=$0} g=="[Panels][WhenOnTop]" && /^(statusBarLeftPadding|statusBarRightPadding|statusBarHeight)=/{print}' "$PLIK_USER")
fi
if [ -n "$NADPIS" ]; then
    blad "$PLIK_USER ma wlasne wartosci w [Panels][WhenOnTop], ktore wygraja z presetem:"
    printf '%s\n' "$NADPIS" >&2
    blad "Usun je (np. kwriteconfig6 --file plasmamobilerc --group Panels --group WhenOnTop --key statusBarLeftPadding --delete) i uruchom ponownie."
    exit 4
fi

# 1. Kopia stanu przed zmiana
KOPIA="$KOPIE/kopia-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$KOPIA/pliki" || { blad "nie moge utworzyc $KOPIA"; exit 5; }
: > "$KOPIA/manifest"
_n=0
for _p in "$PRESET" "$PLIK_ENV"; do
    _n=$((_n + 1))
    if [ -e "$_p" ]; then
        cp -p "$_p" "$KOPIA/pliki/$_n" || { blad "kopia $_p"; exit 5; }
        printf '%s|%s\n' "$_n" "$_p" >> "$KOPIA/manifest"
    else
        printf 'BRAK|%s\n' "$_p" >> "$KOPIA/manifest"
    fi
done
# ~/.config/plasmamobilerc tylko jako dowod (nie zmieniamy go i nie przywracamy,
# bo trzyma tez inne ustawienia powloki, ktore user moze zmienic po instalacji).
[ -r "$PLIK_USER" ] && cp -p "$PLIK_USER" "$KOPIA/plasmamobilerc-uzytkownika.txt"
# poprzednia wielkosc paska (pusta = klucza nie bylo), przywraca ja cofnij.sh
kreadconfig6 --file plasmamobilerc --group General --key statusBarScaleFactor     > "$KOPIA/wielkosc.txt" 2>/dev/null || : > "$KOPIA/wielkosc.txt"

OBJ=$(sciezka_dbus)
{
    echo "data=$(date)"
    echo "id=$ID_URZ ($ZRODLO_ID)"
    echo "skala=$SKALA ($ZRODLO_SKALI)"
    echo "cel_prawy=$CEL_PRAWY cel_lewy=$CEL_LEWY wysokosc=$WYSOKOSC"
    echo "plik_prawy=$PLIK_PRAWY plik_lewy=$PLIK_LEWY"
    echo "obiekt_dbus=$OBJ"
    if [ -n "$OBJ" ]; then
        echo "przed_statusBarLeftPadding=$(odczyt_dbus "$OBJ" statusBarLeftPadding)"
        echo "przed_statusBarRightPadding=$(odczyt_dbus "$OBJ" statusBarRightPadding)"
        echo "przed_statusBarHeight=$(odczyt_dbus "$OBJ" statusBarHeight)"
    fi
    echo "--- apk"
    apk info -v plasma-mobile 2>/dev/null
    echo "--- kscreen-doctor -o"
    kscreen-doctor -o 2>/dev/null | tr -d '\033' | sed 's/\[[0-9;]*m//g'
} > "$KOPIA/stan.txt"
log "Kopia stanu: $KOPIA"
[ -n "$OBJ" ] && zrzut "$KOPIA/przed.png"

# 2. Preset uzytkownika (trwale: envmanager czyta go przy kazdym logowaniu)
mkdir -p "$PRESET_KAT" || { blad "nie moge utworzyc $PRESET_KAT"; exit 5; }
tresc_presetu "$SKALA" "$CEL_PRAWY" "$CEL_LEWY" "$WYSOKOSC" > "$PRESET" || { blad "zapis $PRESET"; exit 5; }
log "Zapisano $PRESET"

# 3. Zastosowanie na zywo
if [ -z "$OBJ" ]; then
    log "plasmashell nie wystawia /Mobile/Panels na D-Bus (brak sesji?)."
    log "Preset wejdzie przy nastepnym logowaniu. Sprawdz potem: sh sprawdz.sh"
    exit 0
fi

ZAPIS=""
if command -v kwriteconfig6 >/dev/null 2>&1; then
    # Te same klucze, ktore envmanager wpisuje z presetu (devicepresets.cpp:80-86)
    _k() { kwriteconfig6 --file "$PLIK_ENV" --group Panels --group WhenOnTop --key "$@"; }
    mkdir -p "$(dirname "$PLIK_ENV")"
    _k statusBarLeftPadding "$PLIK_PRAWY" && _k navigationPanelLeftPadding "$PLIK_PRAWY" \
        && _k statusBarRightPadding "$PLIK_LEWY" && _k navigationPanelRightPadding "$PLIK_LEWY" \
        && ZAPIS="kwriteconfig6"
    if [ -n "$WYSOKOSC" ]; then _k statusBarHeight "$WYSOKOSC"; else _k statusBarHeight --delete; fi
    # wielkosc tresci czyta powloka tylko przy starcie (KCM: "needs restart")
    kwriteconfig6 --file plasmamobilerc --group General --key statusBarScaleFactor "$WIELKOSC"
    systemctl --user restart plasma-plasmashell.service 2>/dev/null && sleep 8
elif command -v plasma-mobile-envmanager >/dev/null 2>&1; then
    case ":$PLASMA_PLATFORM:" in
        *:phone:*)
            # Jak startplasmamobile:29. Bez PLASMA_PLATFORM=phone envmanager przywrocilby
            # ustawienia desktopowe (settings.cpp:45-48), dlatego tylko w tym przypadku.
            QT_QPA_PLATFORM=offscreen plasma-mobile-envmanager --apply-settings && ZAPIS="envmanager" ;;
        *) log "PLASMA_PLATFORM='$PLASMA_PLATFORM' nie zawiera 'phone': envmanager pominiety." ;;
    esac
fi
if [ -z "$ZAPIS" ]; then
    log "Nie zapisalem wartosci dla dzialajacej sesji (brak kwriteconfig6 i envmanagera)."
    log "Preset wejdzie po ponownym zalogowaniu."
    exit 0
fi
log "Wartosci dla sesji zapisane przez $ZAPIS w $PLIK_ENV"

OCZ_L=$(awk -v p="$PLIK_PRAWY" -v s="$SKALA" 'BEGIN{printf "%.4f", p/s}')
OCZ_R=$(awk -v p="$PLIK_LEWY" -v s="$SKALA" 'BEGIN{printf "%.4f", p/s}')

sprawdz_dbus() {
    OBJ=$(sciezka_dbus)
    [ -n "$OBJ" ] || return 1
    DB_L=$(odczyt_dbus "$OBJ" statusBarLeftPadding)
    DB_R=$(odczyt_dbus "$OBJ" statusBarRightPadding)
    log "D-Bus $OBJ: statusBarLeftPadding=$DB_L (oczekiwane $OCZ_L), statusBarRightPadding=$DB_R (oczekiwane $OCZ_R)"
    zgodne "$DB_L" "$OCZ_L" && zgodne "$DB_R" "$OCZ_R"
}

WYNIK=1
if przeladuj_na_zywo; then
    sleep 1
    sprawdz_dbus && WYNIK=0
else
    log "Nie wyslalem sygnalu ConfigChanged (brak busctl i gdbus)."
fi
if [ "$WYNIK" -ne 0 ]; then
    log "Na zywo nie weszlo, probuje restartu samej powloki."
    restart_powloki
    _r=$?
    if [ "$_r" -eq 0 ]; then
        sprawdz_dbus && WYNIK=0
    elif [ "$_r" -eq 2 ]; then
        log "Kopia: $KOPIA  Cofniecie: sh cofnij.sh"
        exit 0
    fi
fi

if [ "$WYNIK" -eq 0 ]; then
    sleep 1
    zrzut "$KOPIA/po.png"
    awk -v s="$SKALA" -v p="$PLIK_PRAWY" -v l="$PLIK_LEWY" -v k="$STALA_LP" -v w="$SZEROKOSC_PANELU" 'BEGIN{
        rp=k*s+p; lp=k*s+l;
        printf "OK. Margines od prawej %.0f px (%.1f px logicznych), od lewej %.0f px (%.1f px logicznych).\n", rp, rp/s, lp, lp/s;
        printf "Zawartosc paska: x od %.0f do %.0f (panel 0..%d).\n", lp, w-rp, w }'
    log "Cofniecie: sh cofnij.sh"
    exit 0
fi
blad "Powloka nie przyjela nowych wartosci. Preset zostal zapisany i wejdzie po ponownym zalogowaniu."
blad "Cofniecie: sh cofnij.sh"
exit 6
