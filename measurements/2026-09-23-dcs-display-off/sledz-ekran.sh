#!/bin/sh
# Zapisuje kazda zmiane stanu DRM (dpms) i panelu (lcd_power) przez 150 s.
D=/sys/class/drm/card0-Unknown-1/dpms
L=/sys/class/lcd/exynos9820-dsim/lcd_power
stary=""
koniec=$(( $(date +%s) + 150 ))
while [ "$(date +%s)" -lt "$koniec" ]; do
	teraz="dpms=$(cat $D) lcd_power=$(cat $L)"
	if [ "$teraz" != "$stary" ]; then
		echo "$(date +%T) $teraz"
		stary=$teraz
	fi
	sleep 0.2
done
echo "--- dmesg sterownika ---"
dmesg | grep -i dsim-lcd || echo "(brak komunikatow)"
