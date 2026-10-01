#!/bin/sh
# Instalacja wtyczki wayfire "podglad" (miniatury okien dla przelacznika
# aplikacji) i gestow przelacznika na telefonie z Droidianem.
# Uruchamiac NA TELEFONIE: sh zainstaluj.sh /sciezka/do/libpodglad.so
# libpodglad.so buduje sie krzyzowo w WSL: ~/droidian/plasma/podglad-buduj.sh
# (sysroot z telefonu, potrzebne wayfire-dev i nlohmann-json3-dev na telefonie).
set -e
SO=${1:-libpodglad.so}
INI=$HOME/.config/plasma-mobile-wf/wayfire.ini

sudo install -m 644 "$SO" /usr/lib/aarch64-linux-gnu/wayfire/libpodglad.so

cp "$INI" "$INI.przed-podgladem"
# wtyczka na liscie plugins (raz)
grep -q "^plugins = .* podglad " "$INI" || sed -i "s/^plugins = ipc ipc-rules /plugins = ipc ipc-rules podglad /" "$INI"

# gesty: prawa krawedz w lewo i dolne rogi w gore otwieraja przelacznik
# powloki; scale i natychmiastowe zamykanie/minimalizacja z rogow wylaczone
CMD="dbus-send --session --type=method_call --dest=org.kde.plasmashell /ScreenGrab pl.s10plus.ScreenGrab.toggleTaskSwitcher"
if ! grep -q "^binding_taskSwitcher " "$INI"; then
    sed -i "/^binding_openAppDrawer = /a\\
command_taskSwitcher = $CMD\\
binding_taskSwitcher = edge-swipe left 1\\
command_taskSwitcherLeft = $CMD\\
binding_taskSwitcherLeft = edge-s1-swipe up 1\\
command_taskSwitcherRight = $CMD\\
binding_taskSwitcherRight = edge-s2-swipe up 1" "$INI"
fi
sed -i -e "s/^toggle = edge-swipe left 1$/toggle = none/" \
       -e "s/^minimize = edge-s2-swipe up 1$/minimize = none/" \
       -e "s/^close = edge-s1-swipe up 1$/close = none/" "$INI"

grep -E "^plugins|taskSwitcher|^toggle|^minimize =|^close =" "$INI"
echo "gotowe; wayfire wczytuje zmiany sam, nowa wtyczka po restarcie sesji"
