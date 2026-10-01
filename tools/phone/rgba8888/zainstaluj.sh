#!/bin/sh
# Build librgba8888.so (eglChooseConfig wrapper, plain C) and preload it into
# maliit-keyboard through a user autostart override.  Uses sudo for /usr/local.
# Undo:  rm ~/.config/autostart/com.github.maliit.keyboard.desktop
set -e
cd "$(dirname "$0")"
command -v gcc >/dev/null || echo 1234 | sudo -S -p "" apt-get -qq install -y gcc >/dev/null
gcc -O2 -fPIC -shared -o librgba8888.so rgba8888.c -ldl
echo 1234 | sudo -S -p "" install -D -m 0644 librgba8888.so /usr/local/lib/rgba8888/librgba8888.so
mkdir -p ~/.config/autostart
sed 's#^Exec=.*#Exec=env LD_PRELOAD=/usr/local/lib/rgba8888/librgba8888.so /usr/bin/maliit-keyboard#' \
    /etc/xdg/autostart/com.github.maliit.keyboard.desktop > ~/.config/autostart/com.github.maliit.keyboard.desktop
grep -n "^Exec" ~/.config/autostart/com.github.maliit.keyboard.desktop
