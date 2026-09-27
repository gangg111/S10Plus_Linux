# wspolne.sh: funkcje wspolne nakladki paska stanu Plasma Mobile dla S10+ (beyond2lte).
# Wczytywany przez zainstaluj.sh, cofnij.sh i sprawdz.sh. Busybox ash, bez bash.
#
# Mechanizm (plasma-mobile 6.7.5, bez zmian w /usr):
#   ~/.local/share/plasma-mobile-device-presets/<id>.conf        (preset uzytkownika)
#     -> plasma-mobile-envmanager przy kazdym logowaniu (startplasmamobile:29)
#     -> ~/.config/plasma-mobile/plasmamobilerc, grupa [Panels][WhenOnTop]
#        (devicepresets.cpp:62-91; klucz nieobecny w presecie jest KASOWANY)
#     -> plasmashell dzieli przez skale wyjscia i wystawia na D-Bus
#        /Mobile/Panels/<wyjscie bez myslnikow> (panelsettingsdbusobjectmanager.cpp:141-161)
#     -> StatusBar.qml:79-80, strony ZAMIENIONE:
#          prawa krawedz = 12 + statusBarLeftPadding  (px logiczne)
#          lewa krawedz  = 12 + statusBarRightPadding (px logiczne)
#
# Cele w pikselach natywnych panelu 1440x3040, liczone od krawedzi ekranu:
#   prawy 350: wyciecie z LineageOS (x 1114..1440, 326 px, overlay config.xml:44)
#              + 21 px kropki prywatnosci jak w AOSP = 347, zaokraglone do 350
#              (ikony koncza sie na x <= 1090)
#   lewy 120:  szacunek szerokosci zakrzywienia 341/4096*1440 (sec,area-size z drzewa
#              producenta, dowod SLABY, do strojenia na oko)
#   26.09.2026 dostrojone na telefonie do ukladu One UI (zdjecie od usera): ikony koncza
#   sie tuz przed aparatem (x ~1070), zegar od x ~110.
CEL_PRAWY_DOMYSLNY=370
CEL_LEWY_DOMYSLNY=110
# Wysokosc paska: tresc jest centrowana w pionie, wiec wysokosc = 2 x srodek otworu
# aparatu. Obrysu otworu nie podaje zaden ROM; ~100 px to szacunek ze zdjecia One UI,
# w ktorym ikony stoja na srodku obiektywow (user: "wycentruj na podstawie srodka aparatu").
WYSOKOSC_DOMYSLNA=200
# statusBarScaleFactor ([General] plasmamobilerc, preset "Large" z KCM powloki): tekst
# 11 x wspolczynnik px logicznych. Zmierzone na telefonie: 1.25 -> cyfry 30 px, 1.5 -> 37 px,
# czyli tyle, ile na zdjeciu One UI (~1,25 raza wiecej niz 30 px).
WIELKOSC_DOMYSLNA=1.5
# Stala czesc marginesu w QML: Kirigami.Units.smallSpacing (4) * 3 = 12 px logicznych
# (kirigami units.cpp:37, qqc2-breeze-style kirigami-plasmadesktop-integration/units.cpp:34)
STALA_LP=12
SZEROKOSC_PANELU=1440

PRESET_KAT="$HOME/.local/share/plasma-mobile-device-presets"
PLIK_ENV="$HOME/.config/plasma-mobile/plasmamobilerc"
PLIK_USER="$HOME/.config/plasmamobilerc"
KOPIE="$HOME/.local/state/nakladka-pasek"
ZNACZNIK="# nakladka-pasek S10+"
USLUGA_POWLOKI="plasma-plasmashell.service"

log() { printf '%s\n' "$*"; }
blad() { printf 'BLAD: %s\n' "$*" >&2; }

liczba() {
    # 0 gdy $1 jest liczba dodatnia (calkowita albo z kropka)
    case "$1" in
        ''|*[!0-9.]*|*.*.*|.) return 1 ;;
    esac
    return 0
}

srodowisko_sesji() {
    # Bierze zmienne sesji z dzialajacego plasmashell (to samo srodowisko, ktore
    # ustawil startplasmamobile), a gdy powloki nie ma: wartosci domyslne.
    : "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"
    export XDG_RUNTIME_DIR
    PID_POWLOKI=$(pidof plasmashell 2>/dev/null | cut -d' ' -f1)
    if [ -n "$PID_POWLOKI" ] && [ -r "/proc/$PID_POWLOKI/environ" ]; then
        _tmp=$(mktemp)
        tr '\000' '\n' < "/proc/$PID_POWLOKI/environ" > "$_tmp"
        while IFS= read -r _l; do
            case "$_l" in
                WAYLAND_DISPLAY=*|DBUS_SESSION_BUS_ADDRESS=*|XDG_CONFIG_DIRS=*|XDG_DATA_DIRS=*|PLASMA_PLATFORM=*)
                    export "$_l" ;;
            esac
        done < "$_tmp"
        rm -f "$_tmp"
    fi
    : "${DBUS_SESSION_BUS_ADDRESS:=unix:path=$XDG_RUNTIME_DIR/bus}"
    : "${WAYLAND_DISPLAY:=wayland-0}"
    export DBUS_SESSION_BUS_ADDRESS WAYLAND_DISPLAY
}

id_urzadzenia() {
    # Ta sama kolejnosc co devicepresets.cpp:29-50: [Device] device z plasmamobilerc
    # wygrywa, inaczej pierwszy wpis /sys/firmware/devicetree/base/compatible.
    ID_URZ=""
    ZRODLO_ID=""
    for _f in "$PLIK_USER" /etc/xdg/plasmamobilerc; do
        [ -r "$_f" ] || continue
        _d=$(awk '/^\[/{g=$0} g=="[Device]" && /^device=/{sub(/^device=/,""); print; exit}' "$_f")
        if [ -n "$_d" ]; then ID_URZ="$_d"; ZRODLO_ID="$_f [Device] device"; return 0; fi
    done
    if [ -r /sys/firmware/devicetree/base/compatible ]; then
        ID_URZ=$(tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | head -n1)
        ZRODLO_ID="/sys/firmware/devicetree/base/compatible"
    fi
    [ -n "$ID_URZ" ]
}

odczytaj_skale() {
    # Kolejnosc: zmienna SKALA, kscreen-doctor -o, ~/.config/kwinoutputconfig.json.
    ZRODLO_SKALI="zmienna SKALA"
    if [ -z "$SKALA" ] && command -v kscreen-doctor >/dev/null 2>&1; then
        SKALA=$(kscreen-doctor -o 2>/dev/null | tr -d '\033' | sed 's/\[[0-9;]*m//g' \
            | grep -o 'Scale: *[0-9.]*' | head -n1 | sed 's/Scale: *//')
        ZRODLO_SKALI="kscreen-doctor -o"
    fi
    if [ -z "$SKALA" ] && [ -r "$HOME/.config/kwinoutputconfig.json" ]; then
        SKALA=$(grep -o '"scale": *[0-9.]*' "$HOME/.config/kwinoutputconfig.json" | head -n1 | sed 's/.*: *//')
        ZRODLO_SKALI="~/.config/kwinoutputconfig.json"
    fi
    if ! liczba "$SKALA"; then
        SKALA=""
        ZRODLO_SKALI="brak"
        return 1
    fi
    return 0
}

oblicz() {
    # $1 cel prawy px, $2 cel lewy px, $3 skala.  plik = cel - 12 * skala (min. 0)
    PLIK_PRAWY=$(awk -v c="$1" -v s="$3" -v k="$STALA_LP" 'BEGIN{v=c-k*s; if(v<0)v=0; printf "%d", v+0.5}')
    PLIK_LEWY=$(awk -v c="$2" -v s="$3" -v k="$STALA_LP" 'BEGIN{v=c-k*s; if(v<0)v=0; printf "%d", v+0.5}')
}

tresc_presetu() {
    # $1 skala, $2 cel prawy, $3 cel lewy, $4 wysokosc paska (puste = domyslna)
    printf '%s (wygenerowane przez zainstaluj.sh dla skali %s)\n' "$ZNACZNIK" "$1"
    printf '# Wartosci w pikselach natywnych panelu 1440x3040; powloka dzieli je przez skale.\n'
    printf '# Cel od krawedzi: prawa %s px (aparat), lewa %s px (krzywizna).\n' "$2" "$3"
    printf '# plik = cel - 12 * skala, bo QML dodaje jeszcze smallSpacing*3 = 12 px logicznych.\n'
    printf '# UWAGA: StatusBar.qml:79-80 zamienia strony paska stanu:\n'
    printf '#   leftPadding  -> PRAWA krawedz ekranu (otwor aparatu)\n'
    printf '#   rightPadding -> LEWA krawedz ekranu (zegar, zakrzywienie)\n'
    printf '# Tylko [Panels][Top]: dolny pasek nawigacji zostaje bez zmian.\n\n'
    printf '[Device]\nname=Samsung Galaxy S10+\n\n'
    printf '[Panels][Top]\n'
    printf 'leftPadding=%s\n' "$PLIK_PRAWY"
    printf 'rightPadding=%s\n' "$PLIK_LEWY"
    if [ -n "$4" ]; then printf 'statusBarHeight=%s\n' "$4"; fi
}

sciezka_dbus() {
    busctl --user tree org.kde.plasmashell 2>/dev/null \
        | grep -o '/Mobile/Panels/[A-Za-z0-9_]*' | sort -u | head -n1
}

odczyt_dbus() {
    # $1 sciezka obiektu, $2 metoda (statusBarLeftPadding itd.); wypisuje liczbe
    busctl --user call org.kde.plasmashell "$1" org.kde.plasmashellMobilePanels "$2" 2>/dev/null \
        | awk '{print $2}'
}

zgodne() {
    # 0 gdy |$1 - $2| < 0.05
    [ -n "$1" ] && [ -n "$2" ] || return 1
    awk -v a="$1" -v b="$2" 'BEGIN{d=a-b; if(d<0)d=-d; exit (d<0.05)?0:1}'
}

przeladuj_na_zywo() {
    # KConfigWatcher w plasmashell slucha sygnalu org.kde.kconfig.notify.ConfigChanged
    # na sciezce /plasmamobilerc i robi reparseConfiguration() (kconfigwatcher.cpp:75-119).
    # Zapis envmanagera idzie na inna sciezke (/plasma_mobile/...), wiec wysylamy sami.
    if command -v busctl >/dev/null 2>&1; then
        busctl --user emit /plasmamobilerc org.kde.kconfig.notify ConfigChanged 'a{saay}' 1 Panels 0 && return 0
    fi
    if command -v gdbus >/dev/null 2>&1; then
        gdbus emit --session --object-path /plasmamobilerc \
            --signal org.kde.kconfig.notify.ConfigChanged "@a{saay} {'Panels': @aay []}" >/dev/null && return 0
    fi
    return 1
}

czekaj_na_powloke() {
    # czeka do 40 s, az plasmashell wystawi obiekt panelu na D-Bus; wypisuje sciezke
    _i=0
    while [ "$_i" -lt 40 ]; do
        _s=$(sciezka_dbus)
        if [ -n "$_s" ]; then printf '%s\n' "$_s"; return 0; fi
        sleep 1
        _i=$((_i + 1))
    done
    return 1
}

restart_powloki() {
    # Restartuje TYLKO plasmashell (usluga uzytkownika). KWin i usluga plasma-mobile
    # zostaja nietkniete: restart plasma-mobile zostawia KWin bez mastera DRM.
    if systemctl --user is-active --quiet "$USLUGA_POWLOKI" 2>/dev/null; then
        log "Restart $USLUGA_POWLOKI (KWin zostaje)..."
        systemctl --user restart "$USLUGA_POWLOKI" || return 1
        sleep 3
        czekaj_na_powloke >/dev/null
        return $?
    fi
    log "plasmashell nie jest usluga systemd uzytkownika ($USLUGA_POWLOKI nieaktywna)."
    log "Zmiana wejdzie po ponownym zalogowaniu (albo ~/narz/sesja-od-nowa.sh przez systemd-run)."
    return 2
}

zrzut() {
    # $1 plik PNG. Spectacle przez KWin (ScreenShot2); ekran musi byc wlaczony.
    command -v spectacle >/dev/null 2>&1 || { log "Brak spectacle, zrzut pominiety."; return 1; }
    _t=""
    command -v timeout >/dev/null 2>&1 && _t="timeout 25"
    QT_QPA_PLATFORM=wayland $_t spectacle -b -n -f -o "$1" >/dev/null 2>&1
    if [ -s "$1" ]; then log "Zrzut: $1"; return 0; fi
    log "Zrzut sie nie udal ($1)."
    return 1
}
