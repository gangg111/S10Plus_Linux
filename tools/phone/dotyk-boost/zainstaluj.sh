#!/bin/sh
# Instalacja podbicia zegara CPU na dotyk.  Uruchamiac jako root.
# Wylaczenie:  systemctl disable --now dotyk-boost
set -e
cd "$(dirname "$0")"
mkdir -p /usr/local/lib/dotyk-boost
install -m 0755 dotyk-boost.py /usr/local/lib/dotyk-boost/
install -m 0644 dotyk-boost.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dotyk-boost.service
systemctl is-active dotyk-boost.service
