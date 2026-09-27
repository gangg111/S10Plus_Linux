#!/bin/sh
# Instalacja huba czujnikow jako uslugi (root).  Moduly brcm_sensorhub i
# kfifo_buf wgrywa tools/pc/wgraj-moduly-extra.sh; jesli leza obok tego
# skryptu, instaluje je tez on.
set -e
cd "$(dirname "$0")"
M=/lib/modules/$(uname -r)/extra
mkdir -p "$M" /usr/local/lib/hubd
for m in brcm_sensorhub.ko kfifo_buf.ko; do
	if [ -f "$m" ]; then install -m 0644 "$m" "$M/"; fi
done
depmod -a
install -m 0644 hubd.py /usr/local/lib/hubd/
install -m 0755 czujniki-wlacz.sh /usr/local/lib/hubd/
install -m 0644 hubd.service /etc/systemd/system/
rm -f /etc/udev/rules.d/61-hub-accel.rules
systemctl daemon-reload
systemctl enable hubd.service
echo zainstalowane
