#!/bin/sh
# Instalacja ochrony glosnikow jako uslugi startowej (root).
set -e
cd "$(dirname "$0")"
install -m 0755 ochrona.py /usr/local/sbin/ochrona-glosnikow
install -m 0644 ochrona-glosnikow.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ochrona-glosnikow.service
systemctl restart ochrona-glosnikow.service
systemctl --no-pager status ochrona-glosnikow.service | tail -6
