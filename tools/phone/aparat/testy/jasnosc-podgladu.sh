#!/bin/sh
# Srednia jasnosc i zywosc srodka podgladu aparatu (dwa zrzuty okna co 1 s), bez
# zapisywania obrazu na stale. Uzycie: sh jasnosc-podgladu.sh [etykieta]
ID=$(python3 /tmp/wfviews.py | awk '/droidian-camera/ && /mapped True/ {print $1; exit}')
for k in 1 2; do
	python3 /tmp/wfcall.py podglad/capture "{\"view-id\": $ID, \"file\": \"/tmp/jp$k.ppm\", \"scale\": 1}" >/dev/null
	sleep 1
done
python3 - "$1" <<'PY'
import sys
from PIL import Image, ImageChops, ImageStat
a = Image.open('/tmp/jp1.ppm').convert('L').crop((0, 300, 1440, 1500))
b = Image.open('/tmp/jp2.ppm').convert('L').crop((0, 300, 1440, 1500))
print('%s: srednia %.1f, roznica klatek %.2f' % (sys.argv[1], ImageStat.Stat(a).mean[0],
      ImageStat.Stat(ImageChops.difference(a, b)).mean[0]))
PY
rm -f /tmp/jp1.ppm /tmp/jp2.ppm
