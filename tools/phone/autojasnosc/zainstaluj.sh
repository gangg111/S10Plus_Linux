#!/bin/sh
# Instalacja automatycznej jasnosci dla sesji Plasmy.
# Uruchamiac jako root (sudo).
#
# pmOS (KWin): usluga uzytkownika systemd, wlaczona dla wszystkich.
#   Wylaczenie:  systemctl --user disable --now autojasnosc
# Droidian (plamo-wf): sesja ma wlasna szyne D-Bus (dbus-run-session), ktorej
#   uslugi systemd nie widza, wiec start idzie przez autostart sesji.
#   Wylaczenie:  rm /etc/xdg/autostart/autojasnosc.desktop
set -e
cd "$(dirname "$0")"
mkdir -p /usr/local/lib/autojasnosc
install -m 0755 autojasnosc.py /usr/local/lib/autojasnosc/
if [ -x /usr/bin/startplasmamobile-wf ]; then
    install -m 0644 autojasnosc.desktop /etc/xdg/autostart/
    echo "zainstalowane (autostart sesji)"
else
    install -m 0644 autojasnosc.service /etc/systemd/user/
    systemctl --global enable autojasnosc.service
    echo "zainstalowane (usluga uzytkownika)"
fi
