#!/bin/sh
# Instalacja automatycznej jasnosci jako uslugi uzytkownika sesji Plasmy.
# Uruchamiac jako root (sudo); usluge wlacza sie dla wszystkich uzytkownikow.
# Wylaczenie:  systemctl --user disable --now autojasnosc
set -e
cd "$(dirname "$0")"
mkdir -p /usr/local/lib/autojasnosc
install -m 0755 autojasnosc.py /usr/local/lib/autojasnosc/
install -m 0644 autojasnosc.service /etc/systemd/user/
systemctl --global enable autojasnosc.service
echo zainstalowane
