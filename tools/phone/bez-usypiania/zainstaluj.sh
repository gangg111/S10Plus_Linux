#!/bin/sh
# Wylacza usypianie telefonu na stale (uspienie zabija UFS: nie wraca z s2idle,
# rootfs idzie w emergency_ro).  Uruchamiac jako user z sudo.
set -eu
K=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for t in sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target; do
	sudo systemctl mask "$t"
done
sudo install -D -m644 "$K/90-bez-usypiania.conf" /etc/systemd/sleep.conf.d/90-bez-usypiania.conf
sudo install -D -m644 "$K/90-logind-bez-usypiania.conf" /etc/systemd/logind.conf.d/90-bez-usypiania.conf
install -m644 "$K/powerdevilrc" "$HOME/.config/powerdevilrc"
sudo systemctl kill -s HUP systemd-logind
echo gotowe
