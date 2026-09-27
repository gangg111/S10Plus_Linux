#!/bin/sh
# Instaluje konfiguracje UCM2 karty beyond-audio (Galaxy S10+) do
# /usr/share/alsa/ucm2 i restartuje PipeWire uzytkownika.
# Uruchamiac na telefonie jako user z prawem sudo:  sh zainstaluj.sh
set -eu
K=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
D=/usr/share/alsa/ucm2
sudo install -D -m644 "$K/ucm2/conf.d/beyond-audio/beyond-audio.conf" \
	"$D/conf.d/beyond-audio/beyond-audio.conf"
sudo install -D -m644 "$K/ucm2/Samsung/beyond/HiFi.conf" "$D/Samsung/beyond/HiFi.conf"
sudo sync "$D/conf.d/beyond-audio/beyond-audio.conf" "$D/Samsung/beyond/HiFi.conf"
# Priorytet wezla sluchawek (osobne urzadzenie PCM), zeby wtyczka przejmowala dzwiek.
install -D -m644 "$K/wireplumber/51-beyond-jack.conf" \
	"$HOME/.config/wireplumber/wireplumber.conf.d/51-beyond-jack.conf"
alsaucm -c hw:0 list _verbs
alsaucm -c hw:0 set _verb HiFi list _devices
systemctl --user restart wireplumber pipewire pipewire-pulse
