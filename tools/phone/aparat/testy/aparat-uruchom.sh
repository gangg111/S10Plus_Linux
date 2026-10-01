#!/bin/sh
# Uruchamia zbudowana aplikacje aparatu w sesji graficznej i sprawdza podglad
# statystyka pikseli (bez zapisywania obrazu na stale): srednia, odchylenie,
# roznica miedzy dwoma zrzutami co 1 s (zywy podglad = roznica > 0).
# Uzycie: sh aparat-uruchom.sh [plik wykonywalny] [czekaj s]
BIN=${1:-$HOME/src/droidian-camera/build/src/droidian-camera}
# Wygaszony panel zatrzymuje wywolania zwrotne ramek Waylanda, a Qt po 100 ms uznaje okno
# za niewidoczne i przestaje rysowac. Stan panelu z podswietlenia (<= 1 = wygaszony),
# nie z dmesg: tamte wpisy wypadaja z bufora jadra.
obudz() {
	if [ "$(cat /sys/class/backlight/panel/brightness)" -le 1 ]; then
		python3 /tmp/wfkey.py >/dev/null; sleep 3
	fi
}
pkill -x droidian-camera; sleep 1; obudz
B=$(dirname $BIN)
(env -i $(cat /tmp/sesja.env | tr '\n' ' ') QT_LOGGING_RULES="*.debug=true;qt.*.debug=false" \
	LD_LIBRARY_PATH=$B/MediaScanner:$B/ThemeUtils DROIDIAN_CAMERA_CAMX=$B/../libcamx.so \
	setsid $BIN > /tmp/aparat-app.log 2>&1 &)
sleep ${2:-8}; obudz
ID=$(python3 /tmp/wfviews.py | awk '/mapped True/ && /toplevel/ && !/DeepSeek|qmlkonsole|Konsole/ {id=$1} END {print id}')
echo "widok: $(python3 /tmp/wfviews.py | awk -v i=$ID '$1==i')"
for k in 1 2; do
	python3 /tmp/wfcall.py podglad/capture "{\"view-id\": $ID, \"file\": \"/tmp/ap$k.ppm\", \"scale\": 1}" >/dev/null
	sleep 1
done
python3 - <<'PY'
from PIL import Image, ImageChops, ImageStat
a = Image.open('/tmp/ap1.ppm').convert('L'); b = Image.open('/tmp/ap2.ppm').convert('L')
sa, sd = ImageStat.Stat(a), ImageStat.Stat(ImageChops.difference(a, b))
print('rozmiar', a.size, 'srednia %.1f odchylenie %.1f' % (sa.mean[0], sa.stddev[0]), 'roznica klatek %.2f' % sd.mean[0])
PY
rm -f /tmp/ap1.ppm /tmp/ap2.ppm
echo "proces: $(pgrep -x droidian-camera)"
grep -iE "error|fail|warn|Detected camera|crash" /tmp/aparat-app.log | sort | uniq -c | head -15 | cut -c1-200
